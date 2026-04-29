from __future__ import annotations

from collections.abc import Callable

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
        "/api/v1/ppt/decks": {"POST"},
        "/api/v1/ppt/decks/{deck_id}/modify": {"POST"},
        "/api/v1/ppt/decks/{deck_id}/export": {"POST"},
        "/api/v1/ppt/themes": {"GET"},
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
            "get",
            "/api/v1/ppt/themes",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]
                == [
                    {"theme_id": "business", "label": "business 商务风"},
                    {"theme_id": "academic", "label": "academic 学术风"},
                    {"theme_id": "apple_black", "label": "apple_black 苹果黑风"},
                    {"theme_id": "apple_white", "label": "apple_white 苹果白风"},
                    {"theme_id": "eco", "label": "eco 绿色环保风"},
                ]
            ),
            None,
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
