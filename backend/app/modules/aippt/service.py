from __future__ import annotations

import inspect
import json
import re
from shutil import copy2
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
from app.modules.aippt.llm_client import DeckPlan, DeckSlide, DeepSeekAIPPTClient
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

    def get_slide_path(self, job_id: str, slide_number: int) -> Path:
        if slide_number < 1 or slide_number > 20:
            raise HTTPException(status_code=404, detail="PPT slide not found.")
        record = self._job_store.read(job_id)
        project_dir = Path(record.project_dir) if record.project_dir else self._job_store.project_dir(job_id)
        path = project_dir / "svg_final" / f"slide_{slide_number:02d}.svg"
        if not path.exists():
            raise HTTPException(status_code=404, detail="PPT slide preview is not ready.")
        return path

    def get_preview(self, job_id: str) -> dict[str, object]:
        record = self._job_store.read(job_id)
        project_dir = Path(record.project_dir) if record.project_dir else self._job_store.project_dir(job_id)
        report_path = project_dir / "generation_report.json"
        deck: dict[str, object] = {}
        if report_path.exists():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if isinstance(report, dict) and isinstance(report.get("deck"), dict):
                    deck = report["deck"]
            except json.JSONDecodeError:
                deck = {}

        page_count = int(deck.get("page_count") or record.page_count)
        slides = deck.get("slides") if isinstance(deck.get("slides"), list) else []
        if not slides:
            slides = [
                {
                    "slide_number": index,
                    "title": f"Slide {index}",
                    "template": "",
                    "right_items": [],
                }
                for index in range(1, page_count + 1)
            ]

        return {
            "job_id": record.job_id,
            "title": deck.get("title") or record.source_name or "AI PPT",
            "subtitle": deck.get("subtitle") or "",
            "page_count": page_count,
            "status": record.status,
            "progress": record.progress,
            "download_url": record.download_url,
            "design_mode": record.design_mode,
            "slides": slides,
        }

    def run_job(self, job_id: str) -> None:
        record = self._job_store.read(job_id)
        project_dir = self._job_store.project_dir(job_id)
        timings: dict[str, float] = {}
        job_started = perf_counter()

        try:
            source_text = self._timed_stage(timings, "parse_source", lambda: self._parse_source(record, project_dir))
            plan = self._timed_stage(timings, "generate_design", lambda: self._generate_design(record, source_text, project_dir))
            record = self._job_store.read(job_id)
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
        edit_context = self._parse_current_ppt_edit_context(source_text)
        if edit_context:
            plan = self._build_current_ppt_edit_plan(source_text, record, edit_context)
            if len(plan.slides) != record.page_count:
                record = self._update_record(record, page_count=len(plan.slides))
            if not edit_context.get("structural_edit"):
                self._copy_unmodified_ppt_assets(
                    source_job_id=edit_context.get("source_job_id"),
                    project_dir=project_dir,
                    target_slides=set(edit_context["target_slides"]),
                )
                self._apply_current_ppt_svg_text_edits(record=record, project_dir=project_dir, edit_context=edit_context)
            self._update_record(record, status="generating_design", progress=18, current_step="生成编辑计划")
        else:
            content_outline = self._generate_content_outline(source_text, record)
            (project_dir / "sources" / "content_outline.md").write_text(content_outline, encoding="utf-8")
            source_text = self._compose_outline_source(source_text, content_outline)
            plan = self._generate_deck_plan(source_text, record)
            setattr(plan, "content_outline", content_outline)
            setattr(plan, "content_outline_path", str(project_dir / "sources" / "content_outline.md"))
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
                    "body_items": list(slide.text_box or slide.bullets or []),
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
            "content_outline": {
                "path": getattr(plan, "content_outline_path", None),
                "excerpt": (getattr(plan, "content_outline", "") or "")[:1200],
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
            metadata["content_outline_path"] = report["content_outline"]["path"]
            metadata["content_outline_excerpt"] = report["content_outline"]["excerpt"]
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

    def _generate_content_outline(self, source_text: str, record: PPTJobRecord) -> str:
        generator = getattr(self._llm_client, "generate_content_outline", None)
        if callable(generator):
            signature = inspect.signature(generator)
            if "design_mode" in signature.parameters:
                return str(generator(source_text, record.page_count, record.style, design_mode=record.design_mode)).strip()
            return str(generator(source_text, record.page_count, record.style)).strip()
        return self._fallback_content_outline(source_text, record.page_count)

    def _compose_outline_source(self, source_text: str, content_outline: str) -> str:
        return "\n\n".join(
            [
                "## 原始需求",
                source_text.strip(),
                "## 详细版内容大纲",
                content_outline.strip(),
                "## PPT 填充要求",
                "请优先使用详细版内容大纲规划每一页，正文不要只写短标签。每页需要有足够解释性文字，同时保持 PPT 可读。",
            ]
        ).strip()

    def _fallback_content_outline(self, source_text: str, page_count: int) -> str:
        topic = source_text.strip().splitlines()[0][:80] or "AI PPT"
        lines = [
            "# 详细版内容大纲",
            "",
            "## Deck narrative",
            f"- 围绕“{topic}”展开背景、问题、方案、执行和收益，每页提供可直接放入 PPT 的正文。",
            "",
            "## Slide-by-slide outline",
        ]
        for index in range(1, page_count + 1):
            lines.extend(
                [
                    f"### 第 {index} 页：{topic} - 关键议题 {index}",
                    f"- 页面目标：说明第 {index} 个关键议题对整体方案的判断价值。",
                    "- 主体内容：",
                    "  - 当前页面需要交代业务背景、用户需求和组织目标，避免只有标题。",
                    "  - 需要补充事实、动作和指标，让读者不依赖口头讲解也能理解结论。",
                    "  - 要点之间需要形成连续叙事，承接上一页并引出下一页。",
                    "  - 每条正文都应该是可直接放入 PPT 的完整业务句子。",
                    "- 视觉建议：使用卡片、流程、对比或指标布局呈现。",
                    "- 右侧标签：背景判断 / 执行动作 / 验收指标",
                    "",
                ]
            )
        return "\n".join(lines).strip()

    def _parse_current_ppt_edit_context(self, source_text: str) -> dict[str, object] | None:
        if "## 当前 PPT" not in source_text or "## 修改要求" not in source_text:
            return None
        if re.search(r"(新建|重新生成|重新做|再生成一份|生成一份新的|生成一个新的)", source_text):
            return None

        current_part, _, trailing = source_text.partition("## 修改要求")
        instruction = trailing.split("##", 1)[0].strip()
        if not instruction:
            return None

        title_match = re.search(r"标题：(.+)", current_part)
        page_count_match = re.search(r"页数：(\d+)", current_part)
        source_job_match = re.search(r"来源\s*Job：([0-9a-fA-F_-]+)", current_part)
        slides = []
        for match in re.finditer(r"-\s*第\s*(\d+)\s*页[：:]\s*(.+?)(?=\n-\s*第\s*\d+\s*页[：:]|\n##|\Z)", current_part, flags=re.S):
            number = int(match.group(1))
            raw = " ".join(match.group(2).split())
            title_text, _, item_text = raw.partition("；要点：")
            items = [item.strip() for item in re.split(r"\s*/\s*", item_text) if item.strip()] if item_text else []
            slides.append({"slide_number": number, "title": title_text.strip(), "items": items})

        if not slides:
            return None
        page_count = int(page_count_match.group(1)) if page_count_match else len(slides)
        target_slides = self._extract_edit_target_slides(instruction, slides)
        page_operations = self._parse_ppt_page_operations(instruction, page_count)
        if page_operations["add_pages"] and not page_operations["delete_pages"] and not page_operations["clear_pages"]:
            target_slides = []
        target_slides = sorted(set(target_slides) | set(page_operations["delete_pages"]) | set(page_operations["clear_pages"]))
        return {
            "title": title_match.group(1).strip() if title_match else "AI PPT",
            "page_count": page_count,
            "source_job_id": source_job_match.group(1) if source_job_match else None,
            "slides": slides,
            "instruction": instruction,
            "target_slides": target_slides,
            "page_operations": page_operations,
            "structural_edit": bool(page_operations["delete_pages"] or page_operations["add_pages"]),
        }

    def _extract_edit_target_slides(self, instruction: str, slides: list[dict[str, object]]) -> list[int]:
        targets: set[int] = set()
        chinese_numbers = {
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        for match in re.finditer(r"第\s*(\d+)\s*(页|张|页幻灯片|张幻灯片)", instruction):
            targets.add(int(match.group(1)))
        for match in re.finditer(r"第\s*([一二两三四五六七八九十])\s*(页|张|页幻灯片|张幻灯片)", instruction):
            targets.add(chinese_numbers.get(match.group(1), 0))
        for match in re.finditer(r"(slide|p)\s*(\d+)", instruction, flags=re.I):
            targets.add(int(match.group(2)))

        if not targets:
            normalized_instruction = instruction.replace(" ", "")
            for slide in slides:
                title = str(slide.get("title") or "")
                number = int(slide.get("slide_number") or 0)
                if title and title in normalized_instruction:
                    targets.add(number)
                elif "总结" in normalized_instruction and "总结" in title:
                    targets.add(number)
                elif "封面" in normalized_instruction and ("封面" in title or number == 1):
                    targets.add(number)

        max_slide = max(int(slide.get("slide_number") or 0) for slide in slides)
        filtered = sorted(number for number in targets if 1 <= number <= max_slide)
        return filtered or [1]

    def _build_current_ppt_edit_plan(self, source_text: str, record: PPTJobRecord, edit_context: dict[str, object]) -> DeckPlan:
        _ = source_text
        instruction = str(edit_context["instruction"])
        target_slides = set(int(number) for number in edit_context["target_slides"])
        slides_payload = list(edit_context["slides"])
        page_operations = edit_context.get("page_operations") if isinstance(edit_context.get("page_operations"), dict) else {}
        delete_pages = {int(number) for number in page_operations.get("delete_pages", [])}
        clear_pages = {int(number) for number in page_operations.get("clear_pages", [])}
        add_pages = [item for item in page_operations.get("add_pages", []) if isinstance(item, dict)]
        source_page_count = max(1, int(edit_context.get("page_count") or record.page_count))
        source_slides = self._apply_ppt_page_operations(slides_payload, delete_pages=delete_pages, add_pages=add_pages, instruction=instruction)
        page_count = max(1, len(source_slides))
        replacement_text = self._extract_ppt_replacement_text(instruction)
        full_text_replacement = replacement_text is not None and self._is_ppt_full_text_replacement(instruction)
        edit_semantics = self._parse_ppt_edit_semantics(instruction)
        source_theme = self._load_source_ppt_theme(edit_context.get("source_job_id"))
        slides: list[DeckSlide] = []
        changed_numbers: set[int] = set()
        for index, source_slide in enumerate(source_slides, start=1):
            old_number = int(source_slide.get("source_slide_number") or source_slide.get("slide_number") or index)
            inserted = bool(source_slide.get("inserted"))
            changed = inserted or old_number in target_slides or old_number in clear_pages
            if changed:
                changed_numbers.add(index)
            number = index
            title = str(source_slide.get("title") or f"第 {number} 页").strip()
            items = [str(item).strip() for item in source_slide.get("items", []) if str(item).strip()]
            source_items = list(items)
            if old_number in clear_pages:
                items = [f"{title}：已按要求删除原正文内容，可在此页重新补充新的说明。"]
                objective = f"删除第 {old_number} 页原正文内容，并保留页面承接关系。"
            elif changed:
                title, items, objective = self._apply_ppt_edit_instruction(
                    title,
                    items,
                    instruction,
                    edit_semantics=edit_semantics,
                    replacement_text=replacement_text,
                    full_text_replacement=full_text_replacement,
                )
            else:
                objective = "保持原页内容与视觉结构不变。"
            should_densify = changed and bool(edit_semantics.get("needs_more_detail") or inserted or old_number in clear_pages) and not full_text_replacement
            template = "three_cards" if should_densify else ("cover" if number == 1 else "three_cards")
            page_rhythm = "dense" if should_densify or number != 1 else "anchor"
            right_source_items = items if old_number in clear_pages else (source_items or items)
            right_items = self._build_ppt_right_labels(title, right_source_items) if should_densify else (items or [title])[:3]
            slides.append(
                DeckSlide(
                    slide_number=number,
                    title=title,
                    objective=objective,
                    bullets=items or [title],
                    visual="current_ppt_edit",
                    template=template,
                    text_box=items or [title],
                    cards=right_items,
                    page_rhythm=page_rhythm,
                )
            )

        theme_colors = source_theme["theme_colors"]
        palette = source_theme["palette"]
        return DeckPlan(
            title=(
                replacement_text
                if full_text_replacement and replacement_text and 1 in target_slides
                else str(edit_context.get("title") or "AI PPT")
            ),
            subtitle=self._ppt_edit_subtitle(source_page_count=source_page_count, final_page_count=page_count, target_slides=changed_numbers or target_slides),
            visual_style=record.style,
            palette=palette,
            slides=slides,
            body_density="dense" if edit_semantics.get("needs_more_detail") else "detailed",
            theme_colors=theme_colors,
            image_resources=[],
            generation_mode="edit_current_ppt",
            execution_mode="free_design" if record.design_mode == "free_design" else "renderer",
            raw_plan_excerpt=instruction[:1200],
        )

    def _apply_ppt_page_operations(
        self,
        slides_payload: list[object],
        *,
        delete_pages: set[int],
        add_pages: list[dict[str, object]],
        instruction: str,
    ) -> list[dict[str, object]]:
        slides = [
            {
                "source_slide_number": int(item.get("slide_number") or index),
                "title": str(item.get("title") or f"第 {index} 页").strip(),
                "items": [str(value).strip() for value in item.get("items", []) if str(value).strip()],
            }
            for index, item in enumerate(slides_payload, start=1)
            if isinstance(item, dict) and int(item.get("slide_number") or index) not in delete_pages
        ]
        for add_index, operation in enumerate(add_pages, start=1):
            insert_after = int(operation.get("after") or len(slides))
            insert_at = max(0, min(insert_after - len([page for page in delete_pages if page <= insert_after]), len(slides)))
            title = str(operation.get("title") or self._infer_added_slide_title(instruction, add_index)).strip()
            items = operation.get("items")
            if not isinstance(items, list) or not items:
                items = self._default_added_slide_items(title)
            slide = {
                "source_slide_number": 0,
                "title": title,
                "items": [str(item).strip() for item in items if str(item).strip()],
                "inserted": True,
            }
            slides.insert(insert_at, slide)
        return slides or [{"source_slide_number": 0, "title": "新增页面", "items": self._default_added_slide_items("新增页面"), "inserted": True}]

    def _parse_ppt_page_operations(self, instruction: str, page_count: int) -> dict[str, object]:
        normalized = re.sub(r"\s+", "", instruction)
        explicit_pages = self._extract_page_references(instruction)
        delete_pages: set[int] = set()
        clear_pages: set[int] = set()
        if "删除" in normalized or "删掉" in normalized or "去掉" in normalized or "移除" in normalized:
            if explicit_pages and any(keyword in normalized for keyword in ("内容", "正文", "要点", "文字")):
                clear_pages.update(explicit_pages)
            elif any(keyword in normalized for keyword in ("删除一页", "删掉一页", "删除一张", "删掉一张", "删除整页", "删掉整页", "移除页面", "去掉页面")):
                delete_pages.update(explicit_pages or [page_count])
            elif any(keyword in normalized for keyword in ("删除内容", "删掉内容", "删除正文", "删掉正文", "清空内容", "清空正文")):
                clear_pages.update(explicit_pages or [1])
            elif explicit_pages and not any(keyword in normalized for keyword in ("内容", "正文", "要点", "文字", "标题")):
                delete_pages.update(explicit_pages)

        add_pages: list[dict[str, object]] = []
        if any(keyword in normalized for keyword in ("增加一页", "新增一页", "添加一页", "插入一页", "加一页", "增加一张", "新增一张")):
            after = explicit_pages[-1] if explicit_pages else page_count
            add_pages.append(
                {
                    "after": after,
                    "title": self._infer_added_slide_title(instruction, 1),
                    "items": self._infer_added_slide_items(instruction),
                }
            )
        return {
            "delete_pages": sorted(number for number in delete_pages if 1 <= number <= page_count),
            "clear_pages": sorted(number for number in clear_pages if 1 <= number <= page_count),
            "add_pages": add_pages,
        }

    def _extract_page_references(self, instruction: str) -> list[int]:
        pages: list[int] = []
        chinese_numbers = {
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        for match in re.finditer(r"第\s*(\d+)\s*(页|张|页幻灯片|张幻灯片)", instruction):
            pages.append(int(match.group(1)))
        for match in re.finditer(r"第\s*([一二两三四五六七八九十])\s*(页|张|页幻灯片|张幻灯片)", instruction):
            pages.append(chinese_numbers.get(match.group(1), 0))
        for match in re.finditer(r"(slide|p)\s*(\d+)", instruction, flags=re.I):
            pages.append(int(match.group(2)))
        deduped: list[int] = []
        for page in pages:
            if page and page not in deduped:
                deduped.append(page)
        return deduped

    def _infer_added_slide_title(self, instruction: str, index: int) -> str:
        patterns = [
            r"(?:增加|新增|添加|插入|加)\s*一[页张].*?(?:标题|主题)?(?:叫|为|是|名为)?[：:「“\"']+\s*([^。；;\n\"”』」]+)",
            r"(?:增加|新增|添加|插入|加)\s*一[页张].*?(?:标题|主题)?(?:叫|为|是|名为)\s*([^。；;\n\"”』」]+)",
            r"(?:增加|新增|添加|插入|加)\s*一[页张]\s*([^。；;\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction)
            if match:
                title = self._clean_ppt_replacement_text(match.group(1))
                title = re.sub(r"^(关于|内容是|页面|作为|用来)", "", title).strip()
                if title:
                    return title[:32]
        return f"新增补充页 {index}"

    def _infer_added_slide_items(self, instruction: str) -> list[str]:
        content_match = re.search(r"(?:内容|要点|正文)\s*(?:包括|包含|写|放|为|是)[：:]*\s*([^。；;\n]+)", instruction)
        if content_match:
            items = [
                item.strip(" ，,、")
                for item in re.split(r"[、/，,；;]", content_match.group(1))
                if item.strip(" ，,、")
            ]
            if items:
                return items[:4]
        title = self._infer_added_slide_title(instruction, 1)
        terms = [term for term in re.split(r"[、/，,；;。\\s]+", title) if term]
        if len(terms) >= 3:
            return terms[:3]
        return self._default_added_slide_items(title)

    def _default_added_slide_items(self, title: str) -> list[str]:
        return [
            f"{title}：补充背景与新增原因",
            f"{title}：说明关键内容与判断依据",
            f"{title}：承接前后页面并给出行动建议",
        ]

    def _ppt_edit_subtitle(self, *, source_page_count: int, final_page_count: int, target_slides: set[int] | list[int]) -> str:
        targets = ", ".join(str(item) for item in sorted(int(number) for number in target_slides)) or "-"
        if final_page_count != source_page_count:
            return f"基于当前 PPT 修改：{source_page_count} 页调整为 {final_page_count} 页，影响第 {targets} 页"
        return f"基于当前 PPT 修改：第 {targets} 页"

    def _apply_current_ppt_svg_text_edits(
        self,
        *,
        record: PPTJobRecord,
        project_dir: Path,
        edit_context: dict[str, object],
    ) -> None:
        _ = record
        instruction = str(edit_context.get("instruction") or "")
        replacement_text = self._extract_ppt_replacement_text(instruction)
        if not replacement_text or not self._is_ppt_title_replacement(instruction):
            return
        source_job_id = edit_context.get("source_job_id")
        if not source_job_id:
            return
        source_dir = self._job_store.project_dir(str(source_job_id))
        if not source_dir.exists():
            return

        slide_lookup = {
            int(slide["slide_number"]): str(slide.get("title") or "")
            for slide in edit_context.get("slides", [])
            if isinstance(slide, dict) and slide.get("slide_number")
        }
        for slide_number in [int(number) for number in edit_context.get("target_slides", [])]:
            old_title = slide_lookup.get(slide_number)
            if not old_title:
                continue
            for folder in ("svg_output", "svg_final"):
                source_path = source_dir / folder / f"slide_{slide_number:02d}.svg"
                if not source_path.exists():
                    continue
                destination_dir = project_dir / folder
                destination_dir.mkdir(parents=True, exist_ok=True)
                svg = source_path.read_text(encoding="utf-8")
                patched = self._replace_svg_text(svg, old_title, replacement_text)
                if patched != svg:
                    (destination_dir / source_path.name).write_text(patched, encoding="utf-8")

    def _replace_svg_text(self, svg: str, old_text: str, new_text: str) -> str:
        candidates = {
            old_text,
            self._escape_xml_text(old_text),
        }
        replacement = self._escape_xml_text(new_text)
        patched = svg
        for candidate in sorted(candidates, key=len, reverse=True):
            if candidate:
                patched = patched.replace(candidate, replacement)
        return patched

    def _escape_xml_text(self, value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _load_source_ppt_theme(self, source_job_id: object) -> dict[str, object]:
        fallback_theme = {
            "bg": "#F8FAFC",
            "panel": "#FFFFFF",
            "primary": "#2563EB",
            "accent": "#DBEAFE",
            "secondary_accent": "#EFF6FF",
            "text": "#0F172A",
            "text_secondary": "#475569",
            "border": "#E2E8F0",
        }
        fallback_palette = [
            fallback_theme["primary"],
            fallback_theme["accent"],
            fallback_theme["secondary_accent"],
        ]
        if not source_job_id:
            return {"theme_colors": fallback_theme, "palette": fallback_palette}

        source_dir = self._job_store.project_dir(str(source_job_id))
        svg_theme = self._read_theme_from_svg_deck(source_dir)
        loaded_theme = self._read_theme_from_job_file(source_dir / "metadata.json")
        if loaded_theme is None:
            loaded_theme = self._read_theme_from_job_file(source_dir / "generation_report.json")

        theme_colors = fallback_theme | (loaded_theme or {}) | (svg_theme or {})
        palette = [
            theme_colors["primary"],
            theme_colors["accent"],
            theme_colors["secondary_accent"],
        ]
        return {"theme_colors": theme_colors, "palette": palette}

    def _read_theme_from_svg_deck(self, source_dir: Path) -> dict[str, str] | None:
        svg_dir = source_dir / "svg_final"
        if not svg_dir.exists() or not any(svg_dir.glob("slide_*.svg")):
            svg_dir = source_dir / "svg_output"
        if not svg_dir.exists():
            return None

        cluster_counts: dict[str, int] = {}
        cluster_colors: dict[str, dict[str, int]] = {}
        for svg_path in sorted(svg_dir.glob("slide_*.svg")):
            try:
                svg = svg_path.read_text(encoding="utf-8")
            except OSError:
                continue
            colors = re.findall(r"#[0-9A-Fa-f]{6}", svg)
            if not colors:
                continue
            counts: dict[str, int] = {}
            for color in colors:
                normalized = color.upper()
                counts[normalized] = counts.get(normalized, 0) + 1
            primary = self._dominant_svg_primary(counts)
            if not primary:
                continue
            cluster_counts[primary] = cluster_counts.get(primary, 0) + 1
            target = cluster_colors.setdefault(primary, {})
            for color, count in counts.items():
                target[color] = target.get(color, 0) + count

        if not cluster_counts:
            return None
        primary = max(cluster_counts, key=lambda color: (cluster_counts[color], sum(cluster_colors[color].values())))
        colors = cluster_colors[primary]
        theme: dict[str, str] = {"primary": primary}

        light_colors = [
            color
            for color in colors
            if color != "#FFFFFF" and self._relative_luminance(color) >= 0.86
        ]
        light_colors.sort(key=lambda color: (colors[color], self._relative_luminance(color)), reverse=True)
        if light_colors:
            theme["bg"] = light_colors[0]
        if "#FFFFFF" in colors:
            theme["panel"] = "#FFFFFF"
        accent_candidates = [color for color in light_colors if color != theme.get("bg")]
        if accent_candidates:
            theme["accent"] = accent_candidates[0]
        if len(accent_candidates) > 1:
            theme["secondary_accent"] = accent_candidates[1]

        dark_colors = [
            color
            for color in colors
            if color != primary and self._relative_luminance(color) < 0.35
        ]
        dark_colors.sort(key=lambda color: (colors[color], -self._relative_luminance(color)), reverse=True)
        if dark_colors:
            theme["text"] = dark_colors[0]
        if len(dark_colors) > 1:
            theme["text_secondary"] = dark_colors[1]

        border_candidates = [
            color
            for color in colors
            if 0.35 <= self._relative_luminance(color) < 0.86 and color != primary
        ]
        border_candidates.sort(key=lambda color: (colors[color], self._relative_luminance(color)), reverse=True)
        if border_candidates:
            theme["border"] = border_candidates[0]
        return theme

    def _dominant_svg_primary(self, colors: dict[str, int]) -> str | None:
        candidates = [
            color
            for color in colors
            if color != "#FFFFFF" and 0.08 < self._relative_luminance(color) < 0.75 and self._saturation(color) >= 0.35
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda color: (colors[color], self._saturation(color)))

    def _relative_luminance(self, color: str) -> float:
        rgb = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4 for channel in rgb]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def _saturation(self, color: str) -> float:
        values = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        maximum = max(values)
        minimum = min(values)
        if maximum == 0:
            return 0.0
        return (maximum - minimum) / maximum

    def _read_theme_from_job_file(self, path: Path) -> dict[str, str] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        candidates = [
            payload.get("theme_colors"),
            payload.get("deck", {}).get("theme_colors") if isinstance(payload.get("deck"), dict) else None,
        ]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            theme = {
                key: str(value).upper()
                for key, value in candidate.items()
                if isinstance(value, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", value.strip())
            }
            if theme:
                return theme
        return None

    def _apply_ppt_edit_instruction(
        self,
        title: str,
        items: list[str],
        instruction: str,
        *,
        edit_semantics: dict[str, object] | None = None,
        replacement_text: str | None = None,
        full_text_replacement: bool = False,
    ) -> tuple[str, list[str], str]:
        cleaned = [item for item in items if item]
        edit_semantics = edit_semantics or self._parse_ppt_edit_semantics(instruction)
        if replacement_text:
            if full_text_replacement:
                return replacement_text, [replacement_text], replacement_text
            if self._is_ppt_title_replacement(instruction):
                return replacement_text, cleaned or [replacement_text], self._ppt_edit_objective(replacement_text, cleaned)
            return title, [replacement_text], replacement_text

        if "删除" in instruction:
            delete_terms = [
                term
                for term in ("总结", "结论", "备注", "说明", "案例", "背景")
                if term in instruction
            ]
            if delete_terms:
                cleaned = [item for item in cleaned if not any(term in item for term in delete_terms)]
            if cleaned != items:
                cleaned = cleaned or [f"{title}：已按要求删除指定内容"]
                return title, cleaned, self._ppt_edit_objective(title, cleaned)

        if edit_semantics.get("needs_more_detail"):
            expanded = self._expand_ppt_slide_items(title, cleaned)
            return title, expanded, self._ppt_edit_objective(title, expanded)

        if not cleaned:
            cleaned = [
                f"{title}：补充背景与核心价值",
                f"{title}：展开应用场景与关键判断",
                f"{title}：强化结论与后续承接",
            ]
            return title, cleaned, self._ppt_edit_objective(title, cleaned)
        cleaned = cleaned[:3]
        return title, cleaned, self._ppt_edit_objective(title, cleaned)

    def _parse_ppt_edit_semantics(self, instruction: str) -> dict[str, object]:
        normalized = re.sub(r"\s+", "", instruction)
        detail_keywords = (
            "详细",
            "扩充",
            "丰富",
            "补充",
            "太少",
            "完善",
            "展开",
            "有点空",
            "太空",
            "空了",
            "空洞",
            "不饱满",
            "内容少",
            "内容太少",
            "信息少",
            "字太少",
            "文字少",
            "文字太少",
            "多写点",
            "写多点",
            "正文多",
            "文字变多",
            "增加文字",
            "加点字",
            "加正文",
        )
        preserve_keywords = ("保留结构", "结构不要动", "不要改变结构", "不改结构", "保持结构", "保留原结构")
        return {
            "needs_more_detail": any(keyword in normalized or keyword in instruction for keyword in detail_keywords),
            "preserve_structure": any(keyword in normalized for keyword in preserve_keywords),
        }

    def _extract_ppt_replacement_text(self, instruction: str) -> str | None:
        patterns = [
            r"(?:改成|改为|换成|替换成|替换为|变成)\s*(?:一句话|一段话|文字|内容|标题)?\s*[：:]\s*(.+)",
            r"(?:改成|改为|换成|替换成|替换为|变成)\s*[“\"']([^”\"']+)[”\"']",
            r"(?:改成|改为|换成|替换成|替换为|变成)\s*「([^」]+)」",
            r"(?:内容|文字|标题)\s*(?:改成|改为|换成|替换成|替换为)\s*(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, instruction, flags=re.S)
            if match:
                text = self._clean_ppt_replacement_text(match.group(1))
                if text:
                    return text
        return None

    def _clean_ppt_replacement_text(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.split(r"\n\s*##|\n\s*生成要求", cleaned, maxsplit=1)[0].strip()
        cleaned = re.split(r"[，,。；;]\s*(?:其他|其余|剩余|其它).*$", cleaned, maxsplit=1)[0].strip()
        cleaned = cleaned.strip("。；; \t\r\n")
        cleaned = cleaned.strip("“”\"'「」")
        return " ".join(cleaned.split())[:120]

    def _is_ppt_title_replacement(self, instruction: str) -> bool:
        return "标题" in instruction or any(keyword in instruction for keyword in ("页名", "页面名称", "slide title"))

    def _is_ppt_full_text_replacement(self, instruction: str) -> bool:
        return any(
            keyword in instruction
            for keyword in (
                "全换掉",
                "全部换掉",
                "全部替换",
                "整页替换",
                "整页改成",
                "文字全换",
                "文字全部",
                "改成一句话",
                "改为一句话",
                "换成一句话",
            )
        )

    def _expand_ppt_slide_items(self, title: str, items: list[str]) -> list[str]:
        seeds = [self._compact_ppt_item_label(item, fallback=title) for item in items[:4] if item]
        if not seeds:
            seeds = [self._compact_ppt_item_label(title, fallback="核心主题")]
        expanded: list[str] = []
        templates = [
            "围绕“{seed}”补充背景、定义和判断依据，让读者先理解它在“{title}”中的位置。",
            "从“{seed}”展开关键构成、典型场景和影响结果，避免页面只停留在概念标签。",
            "结合“{seed}”说明可观察信号、行动抓手和取舍标准，提升页面的信息密度。",
            "补充“{seed}”与前后页面的承接关系，让整套 PPT 的叙事更连贯。",
            "给出“{seed}”对应的结论或建议，帮助读者直接看到下一步应该如何判断。",
            "用“{seed}”补齐风险、边界或验证口径，保证这一页既有观点也有落地依据。",
        ]
        target_count = 6 if len(seeds) >= 3 else 5
        for index in range(target_count):
            seed = seeds[index % len(seeds)]
            expanded.append(templates[index].format(seed=seed, title=title))
        return expanded

    def _build_ppt_right_labels(self, title: str, items: list[str]) -> list[str]:
        labels: list[str] = []
        for item in items:
            label = self._compact_ppt_item_label(item, fallback=title)
            if label and label not in labels:
                labels.append(label)
            if len(labels) >= 3:
                break
        for fallback in ("核心判断", "行动抓手", "验证口径"):
            if fallback not in labels:
                labels.append(fallback)
            if len(labels) >= 3:
                break
        return labels[:3]

    def _compact_ppt_item_label(self, item: str, *, fallback: str) -> str:
        label = re.split(r"[：:，,。；;、/\\|]", item, maxsplit=1)[0].strip() or fallback
        label = re.sub(r"\s+", "", label)
        if len(label) > 8:
            label = label[:8]
        return label

    def _ppt_expansion_suffix(self, item: str, fallback: str) -> str:
        if any(keyword in item for keyword in ("盲盒", "抽取", "复购")):
            return "复购驱动与社交传播"
        if any(keyword in item for keyword in ("设计师", "联名", "稀缺")):
            return "IP联名与稀缺价值"
        if any(keyword in item for keyword in ("衍生", "影视", "游戏", "动漫", "跨界")):
            return "跨界变现与增长空间"
        if any(keyword in item for keyword in ("用户", "消费", "市场")):
            return "需求变化与决策依据"
        if any(keyword in item for keyword in ("方案", "平台", "系统")):
            return "能力闭环与落地路径"
        if any(keyword in item for keyword in ("收益", "价值", "增长")):
            return "业务价值与可衡量结果"
        return fallback

    def _ppt_edit_objective(self, title: str, items: list[str]) -> str:
        if items:
            return f"围绕{title}补充背景、价值和判断依据。"
        return f"补充{title}的核心信息与后续承接。"

    def _copy_unmodified_ppt_assets(self, *, source_job_id: object, project_dir: Path, target_slides: set[int]) -> None:
        if not source_job_id:
            return
        source_job = str(source_job_id)
        source_dir = self._job_store.project_dir(source_job)
        if source_dir == project_dir or not source_dir.exists():
            return

        for folder in ("svg_output", "svg_final", "notes"):
            source_folder = source_dir / folder
            if not source_folder.exists():
                continue
            destination_folder = project_dir / folder
            destination_folder.mkdir(parents=True, exist_ok=True)
            for source_path in source_folder.iterdir():
                slide_number = self._slide_number_from_filename(source_path.name)
                if slide_number is None or slide_number in target_slides:
                    continue
                if not source_path.is_file():
                    continue
                copy2(source_path, destination_folder / source_path.name)

    def _slide_number_from_filename(self, filename: str) -> int | None:
        match = re.search(r"slide_(\d+)", filename)
        if not match:
            return None
        return int(match.group(1))

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
