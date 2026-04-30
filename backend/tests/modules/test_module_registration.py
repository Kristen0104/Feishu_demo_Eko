from __future__ import annotations

from collections.abc import Callable

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
        "/api/v1/auth/feishu/login-url": {"GET"},
        "/api/v1/auth/feishu/callback": {"GET"},
        "/api/v1/auth/me": {"GET"},
        "/api/v1/document/generate": {"POST"},
        "/api/v1/document/generate/stream": {"POST"},
        "/api/v1/document/save": {"POST"},
        "/api/v1/document/test/generate": {"POST"},
        "/api/v1/document/test/save": {"POST"},
        "/api/v1/canvas/sessions/{session_id}": {"GET"},
        "/api/v1/canvas/board/tasks": {"POST"},
        "/api/v1/canvas/board/tasks/{task_id}": {"GET"},
        "/api/v1/canvas/board/tasks/{task_id}/run": {"POST"},
        "/api/v1/agent/tasks": {"POST"},
        "/api/v1/rag/files": {"GET"},
        "/api/v1/feishu/cards/{card_id}": {"GET"},
        "/api/v1/feishu/board/import": {"POST"},
        "/api/v1/feishu/board/create-notes": {"POST"},
        "/api/v1/feishu/board/nodes/{whiteboard_id}": {"GET"},
        "/api/v1/feishu/board/image/{whiteboard_id}": {"GET"},
        "/api/v1/feishu/board/update": {"POST"},
        "/api/v1/feishu/board/delete": {"POST"},
        "/api/v1/feishu/sync/publish": {"POST"},
        "/api/v1/feishu/sync/status/{ticket}": {"GET"},
        "/api/v1/ppt/generate": {"POST"},
        "/api/v1/ppt/design-modes": {"GET"},
        "/api/v1/ppt/jobs/{job_id}": {"GET"},
        "/api/v1/ppt/files/{job_id}": {"GET"},
        "/api/v1/workspace/{workspace_id}": {"GET"},
        "/api/v1/sync/ws/{session_id}": {"GET"},
    }

    assert expected_surface.keys() <= routes.keys()
    for path, methods in expected_surface.items():
        assert routes[path].methods == methods


def test_stub_module_endpoints_return_expected_contracts() -> None:
    client = _build_client()

    cases: list[tuple[str, str, Callable[[dict], bool], dict | None]] = [
        (
            "get",
            "/system/ping",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["status"] == "ok"
                and isinstance(payload["data"]["timestamp"], str)
            ),
            None,
        ),
        (
            "post",
            "/api/v1/document/test/generate",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["session_id"] == "session-123"
                and payload["data"]["status"] == "completed"
                and "# 校园挑战赛方案" in payload["data"]["content"]
            ),
            {
                "session_id": "session-123",
                "topic": "校园挑战赛方案",
                "requirement": "生成一份活动方案",
            },
        ),
        (
            "post",
            "/api/v1/document/test/save",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["session_id"] == "session-123"
                and payload["data"]["status"] == "saved"
            ),
            {
                "session_id": "session-123",
                "title": "校园挑战赛方案",
                "content": "# 校园挑战赛方案",
                "sync_to_feishu": False,
            },
        ),
        (
            "post",
            "/api/v1/canvas/board/tasks",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["message"] == "帮我画一个 AI 应用架构图"
                and payload["data"]["status"] == "pending"
                and payload["data"]["render_mode"] == "create_notes"
            ),
            {
                "message": "帮我画一个 AI 应用架构图",
                "sharing_url": "https://example.feishu.cn/wiki/board/wbcnAABBCC",
            },
        ),
        (
            "post",
            "/api/v1/agent/tasks",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["status"] == "accepted"
            ),
            None,
        ),
        (
            "get",
            "/api/v1/feishu/cards/card-456",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"] == {
                    "card_id": "card-456",
                    "title": "Stub Feishu Card",
                    "platform": "feishu",
                }
            ),
            None,
        ),
        (
            "post",
            "/api/v1/ppt/generate",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["source_name"] == "AI PPT"
                and payload["data"]["page_count"] == 3
                and payload["data"]["status"] == "queued"
                and payload["data"]["job_id"]
            ),
            {"topic": "AI PPT", "page_count": 3, "style": "clean_business"},
        ),
        (
            "get",
            "/api/v1/workspace/workspace-789",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["workspace_id"] == "workspace-789"
                and payload["data"]["role"] == "owner"
                and payload["data"]["locked"] is False
            ),
            None,
        ),
        (
            "get",
            "/api/v1/sync/ws/session-999",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["session_id"] == "session-999"
                and payload["data"]["transport"] == "websocket"
            ),
            None,
        ),
    ]

    for method, path, validator, request_json in cases:
        response = getattr(client, method)(path, json=request_json) if request_json else getattr(client, method)(path)

        assert response.status_code == 200
        assert validator(response.json())
