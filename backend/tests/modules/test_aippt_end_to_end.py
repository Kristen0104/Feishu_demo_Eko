from __future__ import annotations

from pathlib import Path

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
            title="AI PPT E2E",
            subtitle="End-to-end verification deck",
            visual_style="clean editorial deck",
            palette=["#2563EB", "#0F172A", "#E2E8F0"],
            slides=[
                DeckSlide(
                    slide_number=index,
                    title=f"Slide {index}",
                    objective=f"Explain point {index}",
                    bullets=[f"Point {index}.1", f"Point {index}.2", f"Point {index}.3"],
                    visual="cards",
                )
                for index in range(1, page_count + 1)
            ],
        )

    def generate_design_spec(self, source_text: str, page_count: int, style: str, plan: DeckPlan) -> str:
        _ = (source_text, page_count, style, plan)
        return """# Design Spec

## Topic
AI PPT integration

## Format
16:9 PowerPoint

## Visual Style
Clean blue editorial deck

## Slide Count
2 slides
"""

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        _ = (plan, design_spec)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#F8FAFC"/>
  <rect x="0" y="0" width="1280" height="100" fill="#0F172A"/>
  <text x="72" y="68" font-family="Arial" font-size="34" fill="#FFFFFF">{slide.title}</text>
  <text x="72" y="170" font-family="Arial" font-size="24" fill="#2563EB">{slide.objective}</text>
  <rect x="72" y="220" width="1136" height="360" rx="28" fill="#DBEAFE"/>
  <text x="110" y="300" font-family="Arial" font-size="28" fill="#334155">{slide.bullets[0]}</text>
  <text x="110" y="360" font-family="Arial" font-size="28" fill="#334155">{slide.bullets[1]}</text>
  <text x="110" y="420" font-family="Arial" font-size="28" fill="#334155">{slide.bullets[2]}</text>
</svg>"""

    def generate_speaker_notes(self, design_spec: str, source_text: str, plan: DeckPlan) -> str:
        _ = (design_spec, source_text)
        return "\n\n".join(
            f"# slide_{slide.slide_number:02d}\n\nNotes for {slide.title}."
            for slide in plan.slides
        )


def test_aippt_service_exports_real_pptx_with_ppt_master(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    vendor_root = repo_root / "vendor" / "ppt-master"
    assert (vendor_root / "skills" / "ppt-master" / "scripts" / "svg_to_pptx.py").exists()

    settings = Settings(
        AIPPT_STORAGE_DIR=str(tmp_path / "storage"),
        AIPPT_VENDOR_DIR=str(vendor_root),
        AIPPT_REDIS_QUEUE_ENABLED=False,
    )
    service = AIPPTService(
        settings=settings,
        llm_client=FakeLLMClient(),
        runner=PPTMasterRunner(vendor_root),
        parser=FileParser(vendor_root),
        job_store=JobStore(
            jobs_root=settings.AIPPT_STORAGE_PATH / "jobs",
            uploads_root=settings.AIPPT_UPLOADS_PATH,
            projects_root=settings.AIPPT_PROJECTS_PATH,
            exports_root=settings.AIPPT_EXPORTS_PATH,
        ),
    )

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT E2E", page_count=2, style="clean_business")
    )
    service.run_job(job.job_id)

    result = service.get_job(job.job_id)
    export_path = service.get_download_path(job.job_id)

    assert result.status == "done"
    assert result.download_url == f"/api/v1/ppt/files/{job.job_id}"
    assert export_path.exists()
    assert export_path.suffix == ".pptx"
    assert export_path.stat().st_size > 0
