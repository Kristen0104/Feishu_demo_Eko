from __future__ import annotations

import inspect
import json
import re
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from xml.etree import ElementTree
from uuid import uuid4

from fastapi import HTTPException

from app.config import Settings
from app.modules.aippt.file_parser import FileParser
from app.modules.aippt.image_generator import GPTImageGenerator
from app.modules.aippt.job_store import JobStore
from app.modules.aippt.llm_client import DeepSeekAIPPTClient
from app.modules.aippt.ppt_master_runner import PPTMasterRunner
from app.modules.aippt.schemas import PPTGenerationRequest, PPTJobRecord, PPTJobSchema
from app.modules.aippt.spec_lock import SpecLock


MAX_SVG_GENERATION_ATTEMPTS = 2
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_IMAGE_SIGNATURES = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
}


class AIPPTService:
    def __init__(
        self,
        settings: Settings,
        llm_client: DeepSeekAIPPTClient,
        runner: PPTMasterRunner,
        parser: FileParser,
        job_store: JobStore,
        image_generator: GPTImageGenerator | None = None,
    ) -> None:
        self._settings = settings
        self._llm_client = llm_client
        self._image_generator = image_generator or GPTImageGenerator(settings)
        self._runner = runner
        self._parser = parser
        self._job_store = job_store

    def create_job_from_request(
        self,
        payload: PPTGenerationRequest,
        *,
        upload_filename: str | None = None,
        upload_bytes: bytes | None = None,
        image_uploads: list[tuple[str, bytes]] | None = None,
    ) -> PPTJobSchema:
        if upload_bytes and not upload_filename:
            raise ValueError("upload filename is required when upload bytes are provided")
        if not (payload.topic or payload.source_url or upload_bytes):
            raise ValueError("Either topic, source_url, or upload file must be provided.")

        source_type = "topic"
        source_name = payload.topic
        source_path: str | None = None
        job_id = uuid4().hex
        image_uploads = image_uploads or []

        if upload_bytes is not None and upload_filename is not None:
            source_type = "file"
            source_name = upload_filename
            upload_dir = self._job_store.upload_dir(job_id)
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / upload_filename
            file_path.write_bytes(upload_bytes)
            source_path = str(file_path)
        elif payload.source_url:
            source_type = "url"
            source_name = payload.source_url

        if image_uploads:
            images_dir = self._job_store.project_dir(job_id) / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in image_uploads:
                safe_name = self._safe_image_filename(filename)
                self._validate_image_bytes(safe_name, content)
                (images_dir / safe_name).write_bytes(content)

        now = self._now()
        record = PPTJobRecord(
            job_id=job_id,
            status="queued",
            progress=0,
            current_step="任务已入队",
            source_type=source_type,
            source_name=source_name,
            page_count=payload.page_count,
            style=payload.style,
            design_mode=payload.design_mode,
            download_url=None,
            error=None,
            created_at=now,
            updated_at=now,
            source_path=source_path,
            project_dir=str(self._job_store.project_dir(job_id)),
            pptx_path=None,
        )
        self._job_store.write(record)
        return record.to_public()

    def enqueue_job(self, job_id: str) -> None:
        if self._settings.AIPPT_REDIS_QUEUE_ENABLED:
            from app.modules.aippt.tasks import run_ppt_job

            run_ppt_job.delay(job_id)
            return
        self.run_job(job_id)

    def get_job(self, job_id: str) -> PPTJobSchema:
        return self._job_store.read(job_id).to_public()

    def get_download_path(self, job_id: str) -> Path:
        record = self._job_store.read(job_id)
        if record.status != "done" or not record.pptx_path:
            raise HTTPException(status_code=404, detail="PPTX file is not available yet.")
        path = Path(record.pptx_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="PPTX file is missing.")
        return path

    def run_job(self, job_id: str) -> None:
        record = self._job_store.read(job_id)
        project_dir = self._job_store.project_dir(job_id)
        timings: dict[str, float] = {}
        job_started = perf_counter()

        try:
            source_text = self._timed_stage(timings, "parse_source", lambda: self._parse_source(record, project_dir))
            plan = self._timed_stage(timings, "generate_design", lambda: self._generate_design(record, source_text, project_dir))
            image_executor: ThreadPoolExecutor | None = None
            image_future: Future | None = None
            image_started = perf_counter()
            if self._should_generate_images_async(record, plan):
                image_executor = ThreadPoolExecutor(max_workers=1)
                image_future = image_executor.submit(self._generate_images, record, plan, project_dir)
            else:
                self._timed_stage(timings, "generate_images", lambda: self._generate_images(record, plan, project_dir))
            try:
                self._timed_stage(timings, "generate_slides", lambda: self._generate_slides(record, plan, source_text, project_dir, image_future=image_future))
            finally:
                if image_future is not None:
                    image_future.result()
                    timings["generate_images"] = round(perf_counter() - image_started, 3)
                if image_executor is not None:
                    image_executor.shutdown(wait=True)
            self._timed_stage(timings, "generate_notes", lambda: self._generate_notes(record, plan, source_text, project_dir))
            self._timed_stage(timings, "export_pptx", lambda: self._export(record, project_dir))
            timings["total"] = round(perf_counter() - job_started, 3)
            self._write_timing_report(project_dir, timings)
        except Exception as exc:
            timings["total_before_failure"] = round(perf_counter() - job_started, 3)
            self._write_timing_report(project_dir, timings)
            record = self._job_store.read(job_id)
            self._update_record(record, status="failed", error=str(exc), current_step="任务失败")

    def _parse_source(self, record: PPTJobRecord, project_dir: Path) -> str:
        self._prepare_project_dirs(project_dir)
        self._update_record(record, status="parsing_file", progress=5, current_step="解析输入内容")

        source_text: str
        sources_dir = project_dir / "sources"
        source_text_path = sources_dir / "source.md"

        if record.source_type == "topic":
            source_text = record.source_name or ""
        elif record.source_type == "url":
            source_text = self._parser.parse_source_url(record.source_name or "", source_text_path)
        elif record.source_path:
            input_path = Path(record.source_path)
            copied_source = sources_dir / input_path.name
            copied_source.write_bytes(input_path.read_bytes())
            source_text = self._parser.parse_input_file(copied_source)
        else:
            raise RuntimeError("Missing file source for PPT generation.")

        source_text_path.write_text(source_text, encoding="utf-8")
        self._write_metadata(project_dir, record, source_text_path)
        return source_text

    def _generate_design(self, record: PPTJobRecord, source_text: str, project_dir: Path):
        self._update_record(record, status="generating_design", progress=15, current_step="生成设计规范")
        plan = self._generate_deck_plan(source_text, record)
        if getattr(plan, "generation_mode", "") == "fallback":
            self._update_record(record, status="generating_design", progress=18, current_step="生成设计规范（fallback）")
        design_spec = self._llm_client.generate_design_spec(source_text, record.page_count, record.style, plan)
        existing_images = self._existing_image_resources(project_dir)
        if existing_images:
            plan.image_resources = existing_images
            design_spec = self._llm_client.generate_design_spec(source_text, record.page_count, record.style, plan)
        (project_dir / "design_spec.md").write_text(design_spec, encoding="utf-8")
        spec_lock = self._build_spec_lock(plan, record.page_count)
        (project_dir / "spec_lock.md").write_text(spec_lock, encoding="utf-8")
        self._write_image_prompts(project_dir, plan)
        self._write_generation_report(project_dir, record, plan)
        return plan

    def _generate_images(self, record: PPTJobRecord, plan, project_dir: Path) -> None:
        if record.design_mode != "free_design":
            return

        resources = getattr(plan, "image_resources", None) or []
        pending = [item for item in resources if item.get("status", "Pending") == "Pending"]
        if not pending:
            return

        if not self._image_generator.enabled():
            for item in pending:
                item["status"] = "Needs-Manual"
                item["error"] = "AIPPT image generation is disabled or missing AIPPT_IMAGE_API_KEY."
            self._write_image_prompts(project_dir, plan)
            self._write_generation_report(project_dir, record, plan)
            return

        self._update_record(record, status="generating_design", progress=19, current_step=f"生成 {len(pending)} 张图片")
        plan.image_resources = self._image_generator.generate_pending_images(
            resources,
            project_dir,
            lambda item: self._image_prompt_for_resource(item, plan),
        )
        (project_dir / "spec_lock.md").write_text(self._build_spec_lock(plan, record.page_count), encoding="utf-8")
        self._write_image_prompts(project_dir, plan)
        self._write_generation_report(project_dir, record, plan)

    def _generate_slides(self, record: PPTJobRecord, plan, source_text: str, project_dir: Path, *, image_future: Future | None = None) -> None:
        design_spec = (project_dir / "design_spec.md").read_text(encoding="utf-8")
        spec_lock_path = project_dir / "spec_lock.md"
        svg_dir = project_dir / "svg_output"
        total = max(len(plan.slides[: record.page_count]), 1)
        slides = plan.slides[: record.page_count]
        pending_slides = [
            slide for slide in slides
            if not self._has_valid_slide_svg(svg_dir / f"slide_{slide.slide_number:02d}.svg")
        ]

        if not pending_slides:
            self._update_record(
                record,
                status="generating_slides",
                progress=70,
                current_step=f"复用已有 {total}/{total} 页 SVG",
            )
            self._runner.validate_svg_output(project_dir)
            return

        image_blocked_slides = self._image_dependent_slides(record, pending_slides, image_future=image_future)
        early_slides = [slide for slide in pending_slides if slide not in image_blocked_slides]

        if record.design_mode == "free_design" and len(pending_slides) > 1 and self._settings.AIPPT_SLIDE_CONCURRENCY > 1:
            spec_lock = SpecLock.from_file(spec_lock_path)
            max_workers = max(1, min(self._settings.AIPPT_SLIDE_CONCURRENCY, len(pending_slides)))
            completed = total - len(pending_slides)
            self._update_record(
                record,
                status="generating_slides",
                progress=20 + int(completed / total * 50),
                current_step=f"并发生成剩余 {len(pending_slides)}/{total} 页 SVG",
            )
            if early_slides:
                with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(early_slides)))) as executor:
                    futures = {
                        executor.submit(self._generate_valid_slide_svg, plan, slide, design_spec, spec_lock, project_dir=project_dir): slide
                        for slide in early_slides
                    }
                    completed = self._collect_slide_futures(futures, svg_dir, record, completed, total)
            if image_blocked_slides:
                self._wait_for_image_future(record, image_future, project_dir)
                spec_lock = SpecLock.from_file(spec_lock_path)
                for slide in image_blocked_slides:
                    svg = self._generate_valid_slide_svg(plan, slide, design_spec, spec_lock, project_dir=project_dir)
                    (svg_dir / f"slide_{slide.slide_number:02d}.svg").write_text(svg, encoding="utf-8")
                    completed += 1
                    progress = 20 + int(completed / total * 50)
                    self._update_record(
                        record,
                        status="generating_slides",
                        progress=progress,
                        current_step=f"已生成 {completed}/{total} 页 SVG",
                    )
            self._runner.validate_svg_output(project_dir)
            return

        for index, slide in enumerate(slides, start=1):
            slide_path = svg_dir / f"slide_{index:02d}.svg"
            if self._has_valid_slide_svg(slide_path):
                continue
            if slide in image_blocked_slides:
                self._wait_for_image_future(record, image_future, project_dir)
            spec_lock = SpecLock.from_file(spec_lock_path)
            progress = 20 + int((index - 1) / total * 50)
            self._update_record(
                record,
                status="generating_slides",
                progress=progress,
                current_step=f"生成第 {index} 页 SVG",
            )
            svg = self._generate_valid_slide_svg(plan, slide, design_spec, spec_lock, project_dir=project_dir)
            slide_path.write_text(svg, encoding="utf-8")

        self._runner.validate_svg_output(project_dir)

    def _should_generate_images_async(self, record: PPTJobRecord, plan) -> bool:
        if record.design_mode != "free_design":
            return False
        resources = getattr(plan, "image_resources", None) or []
        return any(item.get("status", "Pending") == "Pending" for item in resources)

    def _image_dependent_slides(self, record: PPTJobRecord, slides: list, *, image_future: Future | None) -> list:
        if record.design_mode != "free_design" or image_future is None:
            return []
        return [slide for slide in slides if getattr(slide, "slide_number", None) == 1]

    def _wait_for_image_future(self, record: PPTJobRecord, image_future: Future | None, project_dir: Path) -> None:
        _ = project_dir
        if image_future is None:
            return
        if not image_future.done():
            self._update_record(record, status="generating_slides", progress=45, current_step="等待图片生成完成后合成封面")
        image_future.result()

    def _collect_slide_futures(self, futures: dict[Future, object], svg_dir: Path, record: PPTJobRecord, completed: int, total: int) -> int:
        for future in as_completed(futures):
            slide = futures[future]
            svg = future.result()
            (svg_dir / f"slide_{slide.slide_number:02d}.svg").write_text(svg, encoding="utf-8")
            completed += 1
            progress = 20 + int(completed / total * 50)
            self._update_record(
                record,
                status="generating_slides",
                progress=progress,
                current_step=f"已生成 {completed}/{total} 页 SVG",
            )
        return completed

    def _generate_notes(self, record: PPTJobRecord, plan, source_text: str, project_dir: Path) -> None:
        self._update_record(record, status="generating_notes", progress=80, current_step="生成讲稿 notes")
        design_spec = (project_dir / "design_spec.md").read_text(encoding="utf-8")
        notes = self._llm_client.generate_speaker_notes(design_spec, source_text, plan)
        (project_dir / "notes" / "total.md").write_text(notes, encoding="utf-8")

    def _export(self, record: PPTJobRecord, project_dir: Path) -> None:
        self._update_record(record, status="exporting", progress=90, current_step="导出 PPTX")
        exported_pptx = self._runner.export(project_dir)
        final_export_path = self._runner.copy_export(exported_pptx, self._job_store.export_file(record.job_id))
        self._update_record(
            record,
            status="done",
            progress=100,
            current_step="导出完成",
            pptx_path=str(final_export_path),
            download_url=f"/api/v1/ppt/files/{record.job_id}",
            error=None,
        )

    def _prepare_project_dirs(self, project_dir: Path) -> None:
        (project_dir / "sources").mkdir(parents=True, exist_ok=True)
        (project_dir / "svg_output").mkdir(parents=True, exist_ok=True)
        (project_dir / "notes").mkdir(parents=True, exist_ok=True)
        (project_dir / "svg_final").mkdir(parents=True, exist_ok=True)
        (project_dir / "images").mkdir(parents=True, exist_ok=True)
        (project_dir / "templates").mkdir(parents=True, exist_ok=True)
        (project_dir / "exports").mkdir(parents=True, exist_ok=True)
        readme_path = project_dir / "README.md"
        if not readme_path.exists():
            readme_path.write_text(
                "# AI PPT Project\n\nGenerated by the backend AIPPT workflow and exported through PPT Master.\n",
                encoding="utf-8",
            )

    def _safe_image_filename(self, filename: str) -> str:
        path = Path(filename)
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError(f"Unsupported image file type: {suffix}")
        safe_stem = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in path.stem).strip("._")
        return f"{safe_stem or 'image'}{suffix}"

    def _validate_image_bytes(self, filename: str, content: bytes) -> None:
        suffix = Path(filename).suffix.lower()
        signatures = SUPPORTED_IMAGE_SIGNATURES.get(suffix)
        if not signatures or not any(content.startswith(signature) for signature in signatures):
            raise ValueError(f"Invalid image file content: {filename}")

    def _existing_image_resources(self, project_dir: Path) -> list[dict[str, str]]:
        images_dir = project_dir / "images"
        resources: list[dict[str, str]] = []
        for path in sorted(images_dir.iterdir()) if images_dir.exists() else []:
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                continue
            resources.append(
                {
                    "filename": path.name,
                    "dimensions": "Unknown",
                    "purpose": "User-provided image",
                    "type": "Photography",
                    "status": "Existing",
                    "generation_description": "-",
                }
            )
        return resources

    def _write_metadata(self, project_dir: Path, record: PPTJobRecord, source_text_path: Path) -> None:
        metadata = {
            "job_id": record.job_id,
            "source_type": record.source_type,
            "source_name": record.source_name,
            "page_count": record.page_count,
            "style": record.style,
            "design_mode": record.design_mode,
            "source_text_path": str(source_text_path),
        }
        (project_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_generation_report(self, project_dir: Path, record: PPTJobRecord, plan) -> None:
        templates: dict[str, int] = {}
        slides = []
        for slide in plan.slides[: record.page_count]:
            template = str(slide.template)
            templates[template] = templates.get(template, 0) + 1
            slides.append(
                {
                    "slide_number": slide.slide_number,
                    "title": slide.title,
                    "template": template,
                    "layout_intent": getattr(slide, "layout_intent", None),
                    "page_rhythm": getattr(slide, "page_rhythm", None),
                    "right_items": self._plan_right_items(slide),
                }
            )

        report = {
            "job_id": record.job_id,
            "generated_at": self._now(),
            "planner": {
                "mode": getattr(plan, "generation_mode", "unknown"),
                "fallback_reason": getattr(plan, "fallback_reason", None),
                "raw_plan_excerpt": getattr(plan, "raw_plan_excerpt", None),
            },
            "deck": {
                "title": plan.title,
                "subtitle": plan.subtitle,
                "page_count": record.page_count,
                "style": record.style,
                "design_mode": record.design_mode,
                "execution_mode": getattr(plan, "execution_mode", "renderer"),
                "body_density": getattr(plan, "body_density", "standard"),
                "theme_colors": getattr(plan, "theme_colors", None) or {},
                "template_counts": templates,
                "slides": slides,
            },
            "images": {
                "prompt_document": str(project_dir / "images" / "image_prompts.md"),
                "resources": getattr(plan, "image_resources", None) or [],
            },
            "ppt_master_alignment": {
                "project_dirs": ["sources", "svg_output", "svg_final", "images", "notes", "templates", "exports"],
                "export_order": ["total_md_split.py", "finalize_svg.py", "svg_to_pptx.py -s final"],
                "svg_source_for_export": "svg_final",
            },
        }
        (project_dir / "generation_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        metadata_path = project_dir / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["planner_mode"] = report["planner"]["mode"]
            metadata["fallback_reason"] = report["planner"]["fallback_reason"]
            metadata["raw_plan_excerpt"] = report["planner"]["raw_plan_excerpt"]
            metadata["template_counts"] = templates
            metadata["design_mode"] = record.design_mode
            metadata["execution_mode"] = getattr(plan, "execution_mode", "renderer")
            metadata["body_density"] = getattr(plan, "body_density", "standard")
            metadata["theme_colors"] = getattr(plan, "theme_colors", None) or {}
            metadata["image_prompt_path"] = str(project_dir / "images" / "image_prompts.md")
            metadata["image_resources"] = getattr(plan, "image_resources", None) or []
            metadata["generation_report_path"] = str(project_dir / "generation_report.json")
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_image_prompts(self, project_dir: Path, plan) -> None:
        resources = getattr(plan, "image_resources", None) or []
        prompt_path = project_dir / "images" / "image_prompts.md"
        colors = " | ".join(plan.palette or [])
        lines = [
            "# Image Generation Prompts",
            "",
            f"> Project: {plan.title}",
            f"> Generated: {self._now()}",
            f"> Color scheme: {colors or 'default'}",
            "",
            "---",
            "",
            "## Image List Overview",
            "",
            "| # | Filename | Type | Dimensions | Status |",
            "|---|----------|------|------------|--------|",
        ]
        if resources:
            for index, item in enumerate(resources, start=1):
                lines.append(
                    f"| {index} | {item.get('filename', '')} | {item.get('type', '')} | {item.get('dimensions', '')} | {item.get('status', 'Pending')} |"
                )
        else:
            lines.append("| — | — | — | — | Not-Required |")

        lines.extend(["", "---", "", "## Detailed Prompts", ""])
        if resources:
            for index, item in enumerate(resources, start=1):
                status = item.get("status", "Pending")
                prompt = self._image_prompt_for_resource(item, plan) if status == "Pending" else "No generation required; use the existing file in project/images/."
                negative = self._negative_prompt_for_image_type(item.get("type", "Background")) if status == "Pending" else "-"
                alt_text = item.get("generation_description", "")
                lines.extend(
                    [
                        f"### Image {index}: {item.get('filename', '')}",
                        "",
                        "| Attribute | Value |",
                        "| --------- | ----- |",
                        f"| Purpose | {item.get('purpose', '')} |",
                        f"| Type | {item.get('type', '')} |",
                        f"| Dimensions | {item.get('dimensions', '')} (16:9) |",
                        f"| Original description | {item.get('generation_description', '')} |",
                        "",
                        "**Prompt**:",
                        prompt,
                        "",
                        "**Negative Prompt**:",
                        negative,
                        "",
                        "**Alt Text**:",
                        f"> {alt_text}",
                        "",
                    ]
                )
        else:
            lines.append("No image generation is required for this deck.")

        lines.extend(
            [
                "---",
                "",
                "## Usage Instructions",
                "",
                "1. Generate each `Pending` image with `vendor/ppt-master/skills/ppt-master/scripts/image_gen.py`.",
                "2. Save output files into this project's `images/` directory with the exact filenames above.",
                "3. Mark successful rows as `Generated`; if generation fails after one retry, mark `Needs-Manual` and continue the PPT pipeline.",
            ]
        )
        prompt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def _image_prompt_for_resource(self, item: dict[str, str], plan) -> str:
        description = item.get("generation_description", "")
        image_type = item.get("type", "Background")
        palette = ", ".join(plan.palette or ["#2563EB", "#DBEAFE", "#EFF6FF"])
        if image_type == "Background":
            return (
                f"{description}, professional presentation background, color palette: {palette}, "
                f"visual direction: {getattr(plan, 'visual_style', 'clean professional')}, subtle details, generous negative space for text overlay, "
                "16:9 aspect ratio, high resolution"
            )
        return (
            f"{description}, professional presentation visual, color palette: {palette}, clean composition, "
            "high quality, 16:9 aspect ratio"
        )

    def _negative_prompt_for_image_type(self, image_type: str) -> str:
        if image_type == "Background":
            return "text, letters, watermark, faces, busy patterns, high contrast details"
        if image_type == "Photography":
            return "watermark, text overlay, artificial, CGI, illustration, cartoon, distorted faces"
        if image_type == "Illustration":
            return "realistic, photography, 3D render, complex textures, watermark"
        if image_type == "Diagram":
            return "cluttered, messy, overlapping elements, dark background, realistic"
        return "text, watermark, signature, blurry, distorted, low quality"

    def _plan_right_items(self, slide) -> list[str]:
        template = str(slide.template)
        if template == "architecture":
            return [
                *( [slide.architecture_parent] if getattr(slide, "architecture_parent", None) else [] ),
                *(slide.architecture_items or []),
                *(slide.architecture_flow or []),
            ]
        if template == "comparison":
            return slide.comparison_items or slide.cards or slide.bullets
        if template == "process":
            return slide.process_items or slide.timeline_items or slide.bullets
        if template == "timeline":
            return slide.timeline_items or slide.cards or slide.bullets
        if template == "metrics":
            return slide.metrics or slide.cards or slide.bullets
        return slide.cards or slide.bullets

    def _update_record(self, record: PPTJobRecord, **changes: object) -> PPTJobRecord:
        updated = record.model_copy(update={**changes, "updated_at": self._now()})
        self._job_store.write(updated)
        return updated

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _timed_stage(self, timings: dict[str, float], name: str, callback):
        started = perf_counter()
        try:
            return callback()
        finally:
            timings[name] = round(perf_counter() - started, 3)

    def _write_timing_report(self, project_dir: Path, timings: dict[str, float]) -> None:
        if not project_dir.exists():
            return
        report = {
            "generated_at": self._now(),
            "timings_seconds": timings,
            "slide_concurrency": self._settings.AIPPT_SLIDE_CONCURRENCY,
        }
        (project_dir / "timings.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def _has_valid_slide_svg(self, path: Path) -> bool:
        if not path.exists():
            return False
        try:
            return self._is_ppt_master_safe_svg(path.read_text(encoding="utf-8"))
        except OSError:
            return False

    def _generate_valid_slide_svg(
        self,
        plan,
        slide,
        design_spec: str,
        spec_lock: SpecLock | None = None,
        *,
        project_dir: Path | None = None,
    ) -> str:
        last_svg = ""
        for attempt in range(1, MAX_SVG_GENERATION_ATTEMPTS + 1):
            try:
                last_svg = self._generate_slide_svg(plan, slide, design_spec, spec_lock)
            except Exception as exc:
                if project_dir is not None:
                    debug_dir = project_dir / "debug"
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    (debug_dir / f"slide_{slide.slide_number:02d}_attempt_{attempt}.error.txt").write_text(str(exc), encoding="utf-8")
                if attempt == MAX_SVG_GENERATION_ATTEMPTS:
                    raise
                continue
            if self._is_ppt_master_safe_svg(last_svg):
                return last_svg
            if project_dir is not None:
                debug_dir = project_dir / "debug"
                debug_dir.mkdir(parents=True, exist_ok=True)
                (debug_dir / f"slide_{slide.slide_number:02d}_attempt_{attempt}.svg").write_text(last_svg, encoding="utf-8")
        raise RuntimeError(f"LLM generated invalid SVG for slide_{slide.slide_number:02d}.")

    def _generate_deck_plan(self, source_text: str, record: PPTJobRecord):
        signature = inspect.signature(self._llm_client.generate_deck_plan)
        if "design_mode" in signature.parameters:
            return self._llm_client.generate_deck_plan(
                source_text,
                record.page_count,
                record.style,
                design_mode=record.design_mode,
            )
        return self._llm_client.generate_deck_plan(source_text, record.page_count, record.style)

    def _generate_slide_svg(self, plan, slide, design_spec: str, spec_lock: SpecLock | None) -> str:
        signature = inspect.signature(self._llm_client.generate_slide_svg)
        if "spec_lock" in signature.parameters:
            return self._llm_client.generate_slide_svg(plan, slide, design_spec, spec_lock=spec_lock)
        return self._llm_client.generate_slide_svg(plan, slide, design_spec)

    def _is_ppt_master_safe_svg(self, svg: str) -> bool:
        forbidden = [
            "<foreignObject",
            "<script",
            "<iframe",
            "<style",
            " class=",
            "<textPath",
            "@font-face",
            "<animate",
            "<symbol",
            "rgba(",
            'href="http://',
            "href='http://",
            'href="https://',
            "href='https://",
            'xlink:href="http://',
            "xlink:href='http://",
            'xlink:href="https://',
            "xlink:href='https://",
        ]
        return (
            "<svg" in svg
            and "</svg>" in svg
            and 'viewBox="0 0 1280 720"' in svg
            and not any(item in svg for item in forbidden)
            and not re.search(r"<g\b[^>]*\sopacity=", svg)
            and self._has_visual_content_text(svg)
        )

    def _has_visual_content_text(self, svg: str) -> bool:
        try:
            root = ElementTree.fromstring(svg)
        except ElementTree.ParseError:
            return False
        content_text_count = 0
        any_text_count = 0
        for element in root.iter():
            if self._local_name(element.tag) != "text":
                continue
            try:
                x = float(element.attrib.get("x", "0"))
                y = float(element.attrib.get("y", "0"))
            except ValueError:
                continue
            text = "".join(element.itertext()).strip()
            if text:
                any_text_count += 1
            if y >= 180 and text:
                content_text_count += 1
            if x >= 700 and text:
                return True
            if x >= 300 and y >= 330 and text:
                if content_text_count >= 2:
                    return True
        return content_text_count >= 2 or any_text_count >= 1

    def _local_name(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def _build_spec_lock(self, plan, page_count: int) -> str:
        palette = list(plan.palette or [])
        theme_colors = getattr(plan, "theme_colors", None) or {}
        bg = theme_colors.get("bg", "#F8FAFC")
        panel = theme_colors.get("panel", "#FFFFFF")
        primary = palette[0] if len(palette) > 0 else "#2563EB"
        accent = palette[1] if len(palette) > 1 else "#DBEAFE"
        secondary_accent = palette[2] if len(palette) > 2 else "#EFF6FF"
        text = theme_colors.get("text", "#0F172A")
        text_secondary = theme_colors.get("text_secondary", "#475569")
        border = theme_colors.get("border", "#E2E8F0")
        page_lines = []
        for slide in plan.slides[:page_count]:
            rhythm = self._page_rhythm_for_slide(slide)
            page_lines.append(f"- P{slide.slide_number:02d}: {rhythm}")
        image_lines = []
        for item in getattr(plan, "image_resources", None) or []:
            if item.get("status") in {"Existing", "Generated"} and item.get("filename"):
                key = Path(item["filename"]).stem
                image_lines.append(f"- {key}: images/{item['filename']}")
        images_section = f"\n## images\n{chr(10).join(image_lines)}\n" if image_lines else ""

        return f"""# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## colors
- bg: {bg}
- panel: {panel}
- primary: {primary}
- accent: {accent}
- secondary_accent: {secondary_accent}
- text: {text}
- text_secondary: {text_secondary}
- border: {border}

## typography
- font_family: "Microsoft YaHei", Arial, sans-serif
- title_family: "Microsoft YaHei", Arial, sans-serif
- body_family: "Microsoft YaHei", Arial, sans-serif
- code_family: Consolas, "Courier New", monospace
- body: 22
- title: 34
- subtitle: 20
- annotation: 14

## icons
- library: chunk-filled
- inventory: target, bolt, shield, users, chart-bar, lightbulb
{images_section}

## page_rhythm
{chr(10).join(page_lines)}

## forbidden
- Mixing icon libraries
- rgba()
- <style>, class, <foreignObject>, textPath, @font-face, <animate*>, <script>, <iframe>, <symbol>+<use>
- <g opacity>
""".strip()

    def _page_rhythm_for_slide(self, slide) -> str:
        if getattr(slide, "page_rhythm", None) in {"anchor", "breathing", "dense"}:
            return slide.page_rhythm
        title = str(slide.title).lower()
        if slide.slide_number == 1:
            return "anchor"
        anchor_keywords = ["总结", "结论", "下一步", "next", "thanks", "thank", "qa", "q&a"]
        if any(keyword in title for keyword in anchor_keywords):
            return "anchor"
        normalized = str(slide.template).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"cover", "toc", "chapter", "closing"}:
            return "anchor"
        if normalized in {"timeline", "metrics", "comparison", "process", "architecture", "matrix", "swimlane"}:
            return "dense"
        content_count = len(slide.text_box or slide.bullets or [])
        right_count = len(slide.cards or [])
        if normalized == "three_cards" and content_count <= 2 and right_count <= 1:
            return "breathing"
        return "dense"
