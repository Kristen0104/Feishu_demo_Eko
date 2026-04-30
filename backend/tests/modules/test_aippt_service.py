from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from app.config import Settings
from app.modules.aippt.file_parser import FileParser
from app.modules.aippt.job_store import JobStore
from app.modules.aippt.llm_client import DeckPlan, DeckSlide
from app.modules.aippt.ppt_master_runner import PPTMasterRunner
from app.modules.aippt.schemas import PPTGenerationRequest
from app.modules.aippt.service import AIPPTService


class FakeLLMClient:
    def generate_deck_plan(self, source_text: str, page_count: int, style: str) -> DeckPlan:
        _ = (source_text, style)
        return DeckPlan(
            title="AI PPT",
            subtitle="Generated subtitle",
            visual_style="clean blue dashboard",
            palette=["#2563EB", "#0F172A", "#E2E8F0"],
            slides=[
                DeckSlide(
                    slide_number=index,
                    title=f"Slide {index}",
                    objective=f"Objective {index}",
                    bullets=[f"Bullet {index}.1", f"Bullet {index}.2"],
                    visual="cards",
                )
                for index in range(1, page_count + 1)
            ],
        )

    def generate_design_spec(self, source_text: str, page_count: int, style: str, plan: DeckPlan) -> str:
        _ = (source_text, page_count, style, plan)
        return "# Design Spec\n\n## Topic\nTest"

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        _ = (plan, design_spec)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#ffffff"/>
  <text x="80" y="120" font-family="Arial" font-size="36">{slide.title}</text>
</svg>"""

    def generate_speaker_notes(self, design_spec: str, source_text: str, plan: DeckPlan) -> str:
        _ = (design_spec, source_text)
        return "\n\n".join(
            f"# slide_{slide.slide_number:02d}\n\nNotes for {slide.title}"
            for slide in plan.slides
        )


class RetryThenValidLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.slide_attempts = 0

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        self.slide_attempts += 1
        if self.slide_attempts == 1:
            return """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <foreignObject x="0" y="0" width="100" height="100"><div>bad</div></foreignObject>
</svg>"""
        return super().generate_slide_svg(plan, slide, design_spec)


class PendingImageLLMClient(FakeLLMClient):
    def generate_deck_plan(self, source_text: str, page_count: int, style: str) -> DeckPlan:
        plan = super().generate_deck_plan(source_text, page_count, style)
        plan.image_resources = [
            {
                "filename": "cover_bg.png",
                "dimensions": "1920x1080",
                "purpose": "Cover background",
                "type": "Background",
                "status": "Pending",
                "generation_description": "Should not be generated in template mode.",
            }
        ]
        return plan


class ParallelFreeDesignLLMClient(FakeLLMClient):
    def __init__(self, image_done: threading.Event, allow_image_finish: threading.Event) -> None:
        self.image_done = image_done
        self.allow_image_finish = allow_image_finish
        self.slide_events: list[tuple[int, bool]] = []

    def generate_deck_plan(self, source_text: str, page_count: int, style: str, *, design_mode: str = "template") -> DeckPlan:
        _ = (source_text, style, design_mode)
        return DeckPlan(
            title="Parallel Free Design",
            subtitle="Generated subtitle",
            visual_style="editorial",
            palette=["#2563EB", "#0F172A", "#E2E8F0"],
            execution_mode="free_design",
            image_resources=[
                {
                    "filename": "cover_bg.png",
                    "dimensions": "1920x1080",
                    "purpose": "Cover background",
                    "type": "Background",
                    "status": "Pending",
                    "generation_description": "Background image.",
                }
            ],
            slides=[
                DeckSlide(slide_number=index, title=f"Slide {index}", objective=f"Objective {index}", bullets=["A", "B"])
                for index in range(1, page_count + 1)
            ],
        )

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        self.slide_events.append((slide.slide_number, self.image_done.is_set()))
        if slide.slide_number == 2:
            self.allow_image_finish.set()
        return super().generate_slide_svg(plan, slide, design_spec)


class RecordingImageGenerator:
    def __init__(self) -> None:
        self.called = False

    def enabled(self) -> bool:
        return True

    def generate_pending_images(self, resources, project_dir: Path, prompt_builder):
        _ = (resources, project_dir, prompt_builder)
        self.called = True
        raise AssertionError("template mode must not invoke image generation")


class BlockingImageGenerator:
    def __init__(self, image_started: threading.Event, image_done: threading.Event, allow_finish: threading.Event) -> None:
        self.image_started = image_started
        self.image_done = image_done
        self.allow_finish = allow_finish

    def enabled(self) -> bool:
        return True

    def generate_pending_images(self, resources, project_dir: Path, prompt_builder):
        _ = (project_dir, prompt_builder)
        self.image_started.set()
        assert self.allow_finish.wait(timeout=2)
        updated = []
        for item in resources:
            copied = dict(item)
            copied["status"] = "Generated"
            copied["filename"] = copied.get("filename", "cover_bg.png")
            updated.append(copied)
        self.image_done.set()
        return updated


class FakeRunner(PPTMasterRunner):
    def __init__(self, vendor_root: Path) -> None:
        super().__init__(vendor_root)

    def validate_svg_output(self, project_dir: Path) -> None:
        (project_dir / "svg_quality_report.json").write_text("{}", encoding="utf-8")

    def export(self, project_dir: Path) -> Path:
        exports_dir = project_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        path = exports_dir / "deck_20260429_000000.pptx"
        path.write_bytes(b"fake-pptx")
        return path


def _build_service(
    tmp_path: Path,
    *,
    llm_client: FakeLLMClient | RetryThenValidLLMClient | None = None,
    image_generator=None,
) -> tuple[AIPPTService, Settings]:
    settings = Settings(
        AIPPT_STORAGE_DIR=str(tmp_path / "storage"),
        AIPPT_VENDOR_DIR=str(tmp_path / "vendor" / "ppt-master"),
        AIPPT_REDIS_QUEUE_ENABLED=False,
        AIPPT_SLIDE_CONCURRENCY=2,
    )
    service = AIPPTService(
        settings=settings,
        llm_client=llm_client or FakeLLMClient(),
        runner=FakeRunner(settings.AIPPT_VENDOR_PATH),
        parser=FileParser(settings.AIPPT_VENDOR_PATH),
        job_store=JobStore(
            jobs_root=settings.AIPPT_STORAGE_PATH / "jobs",
            uploads_root=settings.AIPPT_UPLOADS_PATH,
            projects_root=settings.AIPPT_PROJECTS_PATH,
            exports_root=settings.AIPPT_EXPORTS_PATH,
        ),
        image_generator=image_generator,
    )
    return service, settings


def test_aippt_service_creates_project_files_updates_status_and_export(tmp_path) -> None:
    service, settings = _build_service(tmp_path)

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=3, style="clean_business")
    )
    service.run_job(job.job_id)
    result = service.get_job(job.job_id)
    download_path = service.get_download_path(job.job_id)

    project_dir = settings.AIPPT_PROJECTS_PATH / job.job_id
    assert result.status == "done"
    assert result.download_url == f"/api/v1/ppt/files/{job.job_id}"
    assert result.progress == 100
    assert download_path.exists()
    assert (project_dir / "design_spec.md").exists()
    assert (project_dir / "spec_lock.md").exists()
    assert (project_dir / "svg_final").exists()
    assert (project_dir / "images").exists()
    assert (project_dir / "templates").exists()
    assert (project_dir / "exports").exists()
    assert (project_dir / "README.md").exists()
    spec_lock = (project_dir / "spec_lock.md").read_text(encoding="utf-8")
    assert "## canvas" in spec_lock
    assert "- viewBox: 0 0 1280 720" in spec_lock
    assert "## page_rhythm" in spec_lock
    assert "- P01:" in spec_lock
    assert (project_dir / "notes" / "total.md").exists()
    assert (project_dir / "metadata.json").exists()
    assert len(list((project_dir / "svg_output").glob("*.svg"))) == 3


def test_aippt_service_retries_invalid_svg_before_writing_slide(tmp_path) -> None:
    llm_client = RetryThenValidLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=1, style="clean_business")
    )
    service.run_job(job.job_id)

    slide_svg = (settings.AIPPT_PROJECTS_PATH / job.job_id / "svg_output" / "slide_01.svg").read_text(
        encoding="utf-8"
    )
    assert llm_client.slide_attempts == 2
    assert "<foreignObject" not in slide_svg
    assert 'viewBox="0 0 1280 720"' in slide_svg


def test_template_mode_skips_pending_image_generation_even_when_resources_exist(tmp_path) -> None:
    image_generator = RecordingImageGenerator()
    service, _ = _build_service(
        tmp_path,
        llm_client=PendingImageLLMClient(),
        image_generator=image_generator,
    )

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=1, style="ai_image_clean", design_mode="template")
    )
    service.run_job(job.job_id)

    assert service.get_job(job.job_id).status == "done"
    assert image_generator.called is False


def test_free_design_generates_non_image_slides_while_image_generation_runs(tmp_path) -> None:
    image_started = threading.Event()
    image_done = threading.Event()
    allow_image_finish = threading.Event()
    llm_client = ParallelFreeDesignLLMClient(image_done, allow_image_finish)
    image_generator = BlockingImageGenerator(image_started, image_done, allow_image_finish)
    service, _ = _build_service(tmp_path, llm_client=llm_client, image_generator=image_generator)

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=3, style="ai_image_editorial", design_mode="free_design")
    )
    service.run_job(job.job_id)

    assert service.get_job(job.job_id).status == "done"
    assert image_started.is_set()
    assert (2, False) in llm_client.slide_events
    assert (1, True) in llm_client.slide_events


def test_aippt_service_persists_image_uploads_and_records_image_resources(tmp_path) -> None:
    service, settings = _build_service(tmp_path)
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest-image-bytes"

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=2, style="ai_image_clean"),
        image_uploads=[("Cover Hero 01.PNG", png_bytes)],
    )
    service.run_job(job.job_id)

    project_dir = settings.AIPPT_PROJECTS_PATH / job.job_id
    image_path = project_dir / "images" / "Cover_Hero_01.png"
    prompt_path = project_dir / "images" / "image_prompts.md"
    report_path = project_dir / "generation_report.json"

    assert image_path.exists()
    assert image_path.read_bytes() == png_bytes

    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert "Cover_Hero_01.png" in prompt_text
    assert "Existing" in prompt_text
    assert "User-provided image" in prompt_text

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["images"]["resources"] == [
        {
            "filename": "Cover_Hero_01.png",
            "dimensions": "Unknown",
            "purpose": "User-provided image",
            "type": "Photography",
            "status": "Existing",
            "generation_description": "-",
        }
    ]
    assert report["images"]["prompt_document"].endswith("/images/image_prompts.md")


def test_aippt_service_rejects_invalid_image_uploads(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="Unsupported image file type"):
        service.create_job_from_request(
            PPTGenerationRequest(topic="AI PPT", page_count=1, style="ai_image_clean"),
            image_uploads=[
                ("cover.gif", b"GIF89a"),
            ],
        )


def test_aippt_service_rejects_invalid_image_bytes(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="Invalid image file content"):
        service.create_job_from_request(
            PPTGenerationRequest(topic="AI PPT", page_count=1, style="ai_image_clean"),
            image_uploads=[
                ("cover.png", b"not-a-real-png"),
            ],
        )
