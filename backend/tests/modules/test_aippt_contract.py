from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.aippt.dependencies import get_aippt_service
from app.modules.aippt.router import router
from app.modules.aippt.schemas import PPTGenerationRequest, PPTJobSchema


class FakeAIPPTService:
    def __init__(self, export_path: Path) -> None:
        self._export_path = export_path
        self._jobs: dict[str, PPTJobSchema] = {}
        self.enqueued_job_id: str | None = None

    def create_job_from_request(
        self,
        payload: PPTGenerationRequest,
        *,
        upload_filename: str | None = None,
        upload_bytes: bytes | None = None,
    ) -> PPTJobSchema:
        _ = (upload_filename, upload_bytes)
        job = PPTJobSchema(
            job_id="job-123",
            status="queued",
            progress=0,
            current_step="任务已入队",
            source_type="topic",
            source_name=payload.topic,
            page_count=payload.page_count,
            style=payload.style,
            design_mode=payload.design_mode,
            download_url=None,
            error=None,
            created_at="2026-04-29T00:00:00+00:00",
            updated_at="2026-04-29T00:00:00+00:00",
        )
        self._jobs[job.job_id] = job
        return job

    def enqueue_job(self, job_id: str) -> None:
        self.enqueued_job_id = job_id
        self._jobs[job_id] = self._jobs[job_id].model_copy(
            update={
                "status": "generating_slides",
                "progress": 45,
                "current_step": "生成第 3 页 SVG",
                "updated_at": "2026-04-29T00:05:00+00:00",
            }
        )

    def get_job(self, job_id: str) -> PPTJobSchema:
        return self._jobs[job_id]

    def get_download_path(self, job_id: str) -> Path:
        _ = job_id
        return self._export_path


def _build_client(service: FakeAIPPTService) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/ppt")
    app.dependency_overrides[get_aippt_service] = lambda: service
    return TestClient(app)


def test_ppt_design_modes_contract_returns_template_and_free_design(tmp_path) -> None:
    export_path = tmp_path / "job-123.pptx"
    export_path.write_bytes(b"pptx-content")
    client = _build_client(FakeAIPPTService(export_path))

    response = client.get("/api/v1/ppt/design-modes")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == [
        {
            "mode": "template",
            "label": "模板",
            "description": "使用稳定模板布局生成 PPT，速度更快、结果更可控。",
        },
        {
            "mode": "free_design",
            "label": "自由设计",
            "description": "逐页自由设计并可使用生图能力，适合更强视觉表现。",
        },
    ]


def test_ppt_generate_contract_enqueues_job_with_json_payload(tmp_path) -> None:
    export_path = tmp_path / "job-123.pptx"
    export_path.write_bytes(b"pptx-content")
    service = FakeAIPPTService(export_path)
    client = _build_client(service)

    response = client.post(
        "/api/v1/ppt/generate",
        json={"topic": "AI PPT workflow", "page_count": 6, "style": "clean_business"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["status"] == "queued"
    assert payload["data"]["page_count"] == 6
    assert payload["data"]["source_type"] == "topic"
    assert payload["data"]["design_mode"] == "template"
    assert service.enqueued_job_id == "job-123"


def test_ppt_generate_contract_accepts_free_design_json_payload(tmp_path) -> None:
    export_path = tmp_path / "job-123.pptx"
    export_path.write_bytes(b"pptx-content")
    service = FakeAIPPTService(export_path)
    client = _build_client(service)

    response = client.post(
        "/api/v1/ppt/generate",
        json={
            "topic": "AI PPT workflow",
            "page_count": 6,
            "style": "editorial strategy deck",
            "design_mode": "free_design",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["design_mode"] == "free_design"
    assert service.enqueued_job_id == "job-123"


def test_ppt_generate_contract_accepts_file_only_form_payload(tmp_path) -> None:
    export_path = tmp_path / "job-123.pptx"
    export_path.write_bytes(b"pptx-content")
    service = FakeAIPPTService(export_path)
    client = _build_client(service)

    response = client.post(
        "/api/v1/ppt/generate",
        data={"page_count": "4", "style": "clean_business"},
        files={"file": ("brief.md", b"# Campus AI\n\nUse Feishu to improve campus workflows.", "text/markdown")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["page_count"] == 4
    assert payload["data"]["design_mode"] == "template"
    assert service.enqueued_job_id == "job-123"


def test_ppt_generate_contract_accepts_free_design_form_payload(tmp_path) -> None:
    export_path = tmp_path / "job-123.pptx"
    export_path.write_bytes(b"pptx-content")
    service = FakeAIPPTService(export_path)
    client = _build_client(service)

    response = client.post(
        "/api/v1/ppt/generate",
        data={
            "topic": "Campus AI",
            "page_count": "4",
            "style": "editorial strategy deck",
            "design_mode": "free_design",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["job_id"] == "job-123"
    assert payload["data"]["design_mode"] == "free_design"
    assert service.enqueued_job_id == "job-123"


def test_ppt_job_status_and_download_contract(tmp_path) -> None:
    export_path = tmp_path / "job-123.pptx"
    export_path.write_bytes(b"pptx-content")
    client = _build_client(FakeAIPPTService(export_path))

    client.post(
        "/api/v1/ppt/generate",
        json={"topic": "AI PPT workflow", "page_count": 6, "style": "clean_business"},
    )
    status_response = client.get("/api/v1/ppt/jobs/job-123")
    download_response = client.get("/api/v1/ppt/files/job-123")

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["data"]["status"] == "generating_slides"
    assert status_payload["data"]["progress"] == 45
    assert status_payload["data"]["current_step"] == "生成第 3 页 SVG"

    assert download_response.status_code == 200
    assert download_response.content == b"pptx-content"
