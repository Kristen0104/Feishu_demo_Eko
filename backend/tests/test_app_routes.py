from __future__ import annotations

import importlib
import types
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import BaseRoute, Mount

from app.config import Settings
from app.core import container
from app.shared.responses import ApiResponse

AsyncCallable = Callable[[], Awaitable[None]]


@dataclass
class ClientHarness:
    app_factory: Callable[[], TestClient]
    calls: dict[str, bool]
    app: FastAPI
    app_routes: list[BaseRoute]


def build_client_harness(
    monkeypatch: MonkeyPatch,
    *,
    settings: Settings | None = None,
    redis_initializer_override: AsyncCallable | None = None,
) -> ClientHarness:
    calls = {
        "init_db": False,
        "init_redis": False,
        "close_redis": False,
        "dispose_engine": False,
    }

    async def fake_init_db() -> None:
        calls["init_db"] = True
        return None

    async def fake_init_redis() -> None:
        calls["init_redis"] = True
        return None

    async def fake_close_redis() -> None:
        calls["close_redis"] = True
        return None

    class FakeEngine:
        async def dispose(self) -> None:
            calls["dispose_engine"] = True
            return None

    def fake_import_module(module_name: str) -> types.ModuleType:
        if module_name != "app.modules.system.router":
            raise AssertionError(f"unexpected module import: {module_name}")

        module = types.ModuleType(module_name)
        router = APIRouter()

        @router.get("/system/ping")
        async def ping() -> ApiResponse[dict[str, str]]:
            return ApiResponse.success({"status": "ok"})

        module.router = router
        return module

    monkeypatch.setattr(
        container,
        "ROUTER_REGISTRY",
        (("app.modules.system.router", ""),),
    )
    monkeypatch.setattr(container, "import_module", fake_import_module)

    main_module = importlib.import_module("app.main")
    app = main_module.create_app(
        settings=settings or Settings(FRONTEND_STATIC_DIR=None),
        database_initializer=fake_init_db,
        redis_initializer=redis_initializer_override or fake_init_redis,
        redis_closer=fake_close_redis,
        database_engine=FakeEngine(),
    )
    return ClientHarness(
        app_factory=lambda: TestClient(app),
        calls=calls,
        app=app,
        app_routes=list(app.routes),
    )


def test_system_ping_returns_ok_response(monkeypatch) -> None:
    client_harness = build_client_harness(monkeypatch)

    with client_harness.app_factory() as client:
        response = client.get("/system/ping")

        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 0
        assert payload["data"]["status"] == "ok"
        assert client_harness.calls["init_db"] is True
        assert client_harness.calls["init_redis"] is True
        assert client_harness.calls["close_redis"] is False
        assert client_harness.calls["dispose_engine"] is False

    frontend_mounts = [
        route for route in client_harness.app_routes
        if isinstance(route, Mount) and route.path == "/frontend"
    ]
    assert frontend_mounts == []
    assert client_harness.calls["close_redis"] is True
    assert client_harness.calls["dispose_engine"] is True


def test_frontend_mount_and_cors_registration(monkeypatch, tmp_path) -> None:
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    client_harness = build_client_harness(
        monkeypatch,
        settings=Settings(
            FRONTEND_STATIC_DIR=str(frontend_dir),
            CORS_ORIGINS=["https://example.com", "http://localhost:3000"],
        ),
    )

    frontend_mounts = [
        route for route in client_harness.app_routes
        if isinstance(route, Mount) and route.path == "/frontend"
    ]
    assert len(frontend_mounts) == 1

    cors_middleware = next(
        middleware for middleware in client_harness.app.user_middleware
        if isinstance(middleware, Middleware) and middleware.cls is CORSMiddleware
    )
    assert cors_middleware.kwargs["allow_origins"] == [
        "https://example.com",
        "http://localhost:3000",
        "null",
    ]


def test_root_redirects_to_test_frontend(monkeypatch, tmp_path) -> None:
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "test.html").write_text("<html>test</html>", encoding="utf-8")

    client_harness = build_client_harness(
        monkeypatch,
        settings=Settings(FRONTEND_STATIC_DIR=str(frontend_dir)),
    )

    with client_harness.app_factory() as client:
        response = client.get("/", follow_redirects=False)

        assert response.status_code in {307, 308}
        assert response.headers["location"] == "/frontend/test.html"


def test_startup_failure_cleans_initialized_resources(monkeypatch) -> None:
    calls = {
        "init_redis": False,
    }

    async def failing_redis_init() -> None:
        calls["init_redis"] = True
        raise RuntimeError("redis init failed")

    client_harness = build_client_harness(
        monkeypatch,
        redis_initializer_override=failing_redis_init,
    )

    with pytest.raises(RuntimeError, match="redis init failed"):
        with client_harness.app_factory():
            pass

    assert client_harness.calls["init_db"] is True
    assert calls["init_redis"] is True
    assert client_harness.calls["close_redis"] is False
    assert client_harness.calls["dispose_engine"] is True


def test_settings_redis_url_includes_password_when_present() -> None:
    with_password = Settings(
        REDIS_HOST="redis.example.com",
        REDIS_PORT=6380,
        REDIS_DB=2,
        REDIS_PASSWORD="secret",
    )
    without_password = Settings(
        REDIS_HOST="redis.example.com",
        REDIS_PORT=6380,
        REDIS_DB=2,
        REDIS_PASSWORD="",
    )

    assert with_password.REDIS_URL == "redis://:secret@redis.example.com:6380/2"
    assert without_password.REDIS_URL == "redis://redis.example.com:6380/2"


def test_settings_default_feishu_redirect_uri_points_to_frontend_callback() -> None:
    settings = Settings()

    assert settings.FEISHU_OAUTH_REDIRECT_URI == "http://127.0.0.1:3002/login/feishu/callback"
    assert settings.FRONTEND_LOGIN_SUCCESS_URL == "http://127.0.0.1:3002/home"


def test_team_router_is_registered_in_container_registry() -> None:
    assert ("app.modules.team.router", "/api/v1/team") in container.ROUTER_REGISTRY
