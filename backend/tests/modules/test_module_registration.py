from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core import container
from app.modules.aippt.dependencies import get_aippt_service
from app.modules.aippt.schemas import PPTGenerationRequest, PPTJobSchema


class FakeAIPPTService:
    def __init__(self) -> None:
        self._job = PPTJobSchema(
            job_id="stub-ppt-job",
            status="queued",
            progress=0,
            current_step="任务已入队",
            source_type="topic",
            source_name="AI PPT",
            page_count=3,
            style="clean_business",
            download_url=None,
            error=None,
            created_at="2026-04-29T00:00:00+00:00",
            updated_at="2026-04-29T00:00:00+00:00",
        )

    def create_job_from_request(
        self,
        payload: PPTGenerationRequest,
        *,
        upload_filename: str | None = None,
        upload_bytes: bytes | None = None,
    ) -> PPTJobSchema:
        _ = (upload_filename, upload_bytes)
        self._job = self._job.model_copy(
            update={
                "source_name": payload.topic or payload.source_url,
                "page_count": payload.page_count,
                "style": payload.style,
            }
        )
        return self._job

    def enqueue_job(self, job_id: str) -> None:
        _ = job_id

    def get_job(self, job_id: str) -> PPTJobSchema:
        _ = job_id
        return self._job


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
    app.dependency_overrides[get_aippt_service] = lambda: FakeAIPPTService()
    return TestClient(app)


def test_register_routers_mounts_expected_paths() -> None:
    app = FastAPI()
    container.register_routers(app)

    routes = {
        route.path: route
        for route in app.routes
        if isinstance(route, APIRoute)
    }

    expected_surface = {
        "/system/ping": {"GET"},
        "/api/v1/auth/feishu/login": {"POST"},
        "/api/v1/auth/me": {"GET"},
        "/api/v1/canvas/sessions/{session_id}": {"GET"},
        "/api/v1/agent/tasks": {"POST"},
        "/api/v1/ppt/generate": {"POST"},
        "/api/v1/ppt/jobs/{job_id}": {"GET"},
        "/api/v1/ppt/files/{job_id}": {"GET"},
        "/api/v1/rag/files": {"GET"},
        "/api/v1/feishu/cards/{card_id}": {"GET"},
        "/api/v1/workspace/{workspace_id}": {"GET"},
        "/api/v1/sync/ws/{session_id}": {"GET"},
    }

    assert expected_surface.keys() <= routes.keys()
    for path, methods in expected_surface.items():
        assert routes[path].methods == methods


def test_stub_module_endpoints_return_expected_contracts() -> None:
    client = _build_client()

    cases = [
        (
            "get",
            "/api/v1/canvas/sessions/session-123",
            {
                "data": {
                    "session_id": "session-123",
                    "title": "Stub Canvas Session",
                    "mode": "canvas",
                },
            },
        ),
        (
            "post",
            "/api/v1/agent/tasks",
            {
                "data": {
                    "task_id": "stub-task",
                    "status": "accepted",
                },
            },
        ),
        (
            "get",
            "/api/v1/rag/files",
            {
                "data": [
                    {
                        "file_id": "stub-file",
                        "filename": "knowledge-base.md",
                        "source": "stub",
                    }
                ],
            },
        ),
        (
            "get",
            "/api/v1/feishu/cards/card-456",
            {
                "data": {
                    "card_id": "card-456",
                    "title": "Stub Feishu Card",
                    "platform": "feishu",
                },
            },
        ),
        (
            "get",
            "/api/v1/workspace/workspace-789",
            {
                "data": {
                    "workspace_id": "workspace-789",
                    "role": "owner",
                    "locked": False,
                },
            },
        ),
        (
            "get",
            "/api/v1/sync/ws/session-999",
            {
                "data": {
                    "session_id": "session-999",
                    "transport": "websocket",
                },
            },
        ),
    ]

    for method, path, expected in cases:
        response = getattr(client, method)(path)

        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 0
        assert payload["message"] == "success"
        assert payload["data"] == expected["data"]

    aippt_response = client.post(
        "/api/v1/ppt/generate",
        json={"topic": "AI PPT", "page_count": 3, "style": "clean_business"},
    )
    assert aippt_response.status_code == 200
    aippt_payload = aippt_response.json()
    assert aippt_payload["code"] == 0
    assert aippt_payload["data"]["source_name"] == "AI PPT"
    assert aippt_payload["data"]["page_count"] == 3
    assert aippt_payload["data"]["status"] == "queued"
    assert aippt_payload["data"]["job_id"]
