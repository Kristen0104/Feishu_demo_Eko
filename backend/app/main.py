"""
Eko AI Agent 后端服务入口
基于 FastAPI 框架，提供 RESTful API 和 WebSocket 支持

主要功能：
- 会话管理与 Agent 执行
- RAG 知识库
- Canvas 白板协作
- 飞书集成（WebSocket 长连接）
"""
import asyncio
import logging
import subprocess
import sys
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.core.container import register_routers
from app.core.database import engine, init_db
from app.core.redis_client import close_redis, init_redis
from app.modules.sync.manager import get_sync_connection_manager

AsyncCallable = Callable[[], Awaitable[None]]
RouterRegistrar = Callable[[FastAPI], None]
logger = logging.getLogger(__name__)


def configure_middlewares(app: FastAPI, settings: Settings) -> None:
    allowed_origins = list(settings.CORS_ORIGINS)
    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",
    ):
        if origin not in allowed_origins:
            allowed_origins.append(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


async def log_requests(request: Request, call_next) -> Any:
    start = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration = perf_counter() - start
        logger.exception(
            "%s %s - failed - %.3fs",
            request.method,
            request.url.path,
            duration,
        )
        raise

    duration = perf_counter() - start
    logger.info(
        "%s %s - %s - %.3fs",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


def maybe_mount_frontend(app: FastAPI, settings: Settings) -> None:
    if settings.FRONTEND_STATIC_DIR:
        app.mount(
            "/frontend",
            StaticFiles(directory=settings.FRONTEND_STATIC_DIR, html=True),
            name="frontend",
        )


def maybe_mount_root_frontend(app: FastAPI, settings: Settings) -> None:
    if settings.FRONTEND_STATIC_DIR:

        @app.get("/", include_in_schema=False)
        async def root() -> RedirectResponse:
            return RedirectResponse(url="/frontend/test.html")


def build_lifespan(
    *,
    settings: Settings,
    database_initializer: AsyncCallable,
    redis_initializer: AsyncCallable,
    redis_closer: AsyncCallable,
    database_engine: Any,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_initialized = False
        redis_initialized = False
        sync_forwarder_started = False
        feishu_ws_stop_event: asyncio.Event | None = None
        feishu_ws_monitor_task: asyncio.Task[None] | None = None

        try:
            await database_initializer()
            db_initialized = True
            await redis_initializer()
            redis_initialized = True
            await get_sync_connection_manager().start_redis_forwarder()
            sync_forwarder_started = True
            if settings.FEISHU_WS_AUTO_START:
                feishu_ws_stop_event = asyncio.Event()
                feishu_ws_monitor_task = asyncio.create_task(
                    supervise_feishu_ws_listener(settings, feishu_ws_stop_event)
                )
            yield
        finally:
            if feishu_ws_stop_event is not None:
                feishu_ws_stop_event.set()
            if feishu_ws_monitor_task is not None:
                await feishu_ws_monitor_task
            if sync_forwarder_started:
                await get_sync_connection_manager().stop_redis_forwarder()
            if redis_initialized:
                await redis_closer()
            if db_initialized:
                await database_engine.dispose()

    return lifespan


def maybe_start_feishu_ws_listener(settings: Settings) -> subprocess.Popen[Any] | None:
    if not settings.FEISHU_WS_AUTO_START:
        return None
    if not settings.FEISHU_APP_ID or not settings.FEISHU_APP_SECRET:
        logger.info("Feishu WS listener auto-start skipped because credentials are missing")
        return None

    backend_dir = Path(__file__).resolve().parents[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "app.modules.feishu.ws_listener"],
        cwd=str(backend_dir),
        start_new_session=True,
    )
    logger.info("Feishu WS listener auto-started pid=%s", process.pid)
    return process


async def supervise_feishu_ws_listener(
    settings: Settings,
    stop_event: asyncio.Event,
) -> None:
    process = maybe_start_feishu_ws_listener(settings)
    try:
        while not stop_event.is_set():
            if process is not None and process.poll() is not None:
                logger.warning(
                    "Feishu WS listener exited code=%s; restarting",
                    process.returncode,
                )
                process = maybe_start_feishu_ws_listener(settings)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
    finally:
        if process is not None:
            stop_feishu_ws_listener(process)


def stop_feishu_ws_listener(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    logger.info("Stopping Feishu WS listener pid=%s", process.pid)
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        logger.warning("Feishu WS listener did not stop in time; killing pid=%s", process.pid)
        process.kill()
        process.wait(timeout=5)


def create_app(
    *,
    settings: Settings | None = None,
    router_registrar: RouterRegistrar = register_routers,
    database_initializer: AsyncCallable = init_db,
    redis_initializer: AsyncCallable = init_redis,
    redis_closer: AsyncCallable = close_redis,
    database_engine: Any = engine,
) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(
        title=app_settings.APP_NAME,
        version=app_settings.APP_VERSION,
        lifespan=build_lifespan(
            settings=app_settings,
            database_initializer=database_initializer,
            redis_initializer=redis_initializer,
            redis_closer=redis_closer,
            database_engine=database_engine,
        ),
    )

    maybe_mount_frontend(app, app_settings)
    maybe_mount_root_frontend(app, app_settings)
    configure_middlewares(app, app_settings)
    app.middleware("http")(log_requests)
    router_registrar(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
