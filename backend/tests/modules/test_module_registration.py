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
        "/api/v1/document/generate": {"POST"},
        "/api/v1/document/generate/stream": {"POST"},
        "/api/v1/document/save": {"POST"},
        "/api/v1/document/test/generate": {"POST"},
        "/api/v1/document/test/save": {"POST"},
        "/api/v1/feishu/cards/{card_id}": {"GET"},
        "/api/v1/feishu/sync/publish": {"POST"},
        "/api/v1/feishu/sync/status/{ticket}": {"GET"},
    }

    assert expected_surface.keys() <= routes.keys()
    for path, methods in expected_surface.items():
        assert routes[path].methods == methods


def test_stub_module_endpoints_return_expected_contracts() -> None:
    client = _build_client()

    cases = [
        (
            "get",
            "/system/ping",
            lambda payload: (
                payload["code"] == 0
                and payload["message"] == "success"
                and payload["data"]["status"] == "ok"
                and isinstance(payload["data"]["timestamp"], str)
            ),
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
        ),
    ]

    for case in cases:
        if len(case) == 4:
            method, path, validator, request_json = case
            response = getattr(client, method)(path, json=request_json)
        else:
            method, path, validator = case
            response = getattr(client, method)(path)

        assert response.status_code == 200
        payload = response.json()
        assert validator(payload)
