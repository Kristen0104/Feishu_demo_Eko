from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core import container


def _build_client() -> TestClient:
    app = FastAPI()
    container.register_routers(app)
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
        "/api/v1/canvas/board/tasks": {"POST"},
        "/api/v1/canvas/board/tasks/{task_id}": {"GET"},
        "/api/v1/agent/tasks": {"POST"},
        "/api/v1/rag/files": {"GET"},
        "/api/v1/feishu/cards/{card_id}": {"GET"},
        "/api/v1/feishu/board/import": {"POST"},
        "/api/v1/feishu/board/create-notes": {"POST"},
        "/api/v1/feishu/board/nodes/{whiteboard_id}": {"GET"},
        "/api/v1/feishu/board/image/{whiteboard_id}": {"GET"},
        "/api/v1/feishu/board/update": {"POST"},
        "/api/v1/feishu/board/delete": {"POST"},
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
            "/api/v1/canvas/board/tasks",
            {
                "json": {
                    "message": "帮我画一个 AI 应用架构图",
                    "sharing_url": "https://example.feishu.cn/wiki/board/wbcnAABBCC",
                },
                "data": {
                    "message": "帮我画一个 AI 应用架构图",
                    "sharing_url": "https://example.feishu.cn/wiki/board/wbcnAABBCC",
                    "status": "pending",
                    "current_step": "pending",
                    "render_mode": "create_notes",
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
            "post",
            "/api/v1/feishu/board/import",
            {
                "json": {
                    "whiteboard_id": "wbcn123",
                    "source": "flowchart TD\nA-->B",
                    "source_type": "content",
                    "syntax": "mermaid",
                    "diagram_type": "flowchart",
                    "style": "board",
                },
                "data": {
                    "whiteboard_id": "wbcn123",
                    "syntax": "mermaid",
                    "diagram_type": "flowchart",
                },
            },
        ),
        (
            "post",
            "/api/v1/feishu/board/create-notes",
            {
                "json": {
                    "whiteboard_id": "wbcn123",
                    "nodes": [{"type": "composite_shape", "text": {"text": "A"}}],
                    "source_type": "content",
                    "client_token": "",
                    "user_id_type": "open_id",
                },
                "data": {
                    "whiteboard_id": "wbcn123",
                    "count": 1,
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
        kwargs = {}
        if "json" in expected:
            kwargs["json"] = expected["json"]
        response = getattr(client, method)(path, **kwargs)

        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 0
        assert payload["message"] == "success"
        if isinstance(expected["data"], list):
            assert payload["data"] == expected["data"]
            continue
        for key, value in expected["data"].items():
            assert payload["data"][key] == value
