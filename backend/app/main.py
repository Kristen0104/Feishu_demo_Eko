"""
Eko AI Agent 后端服务入口
基于 FastAPI 框架，提供 RESTful API 和 WebSocket 支持

主要功能：
- 会话管理与 Agent 执行
- RAG 知识库
- Canvas 白板协作
- 飞书集成（WebSocket 长连接）
"""
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.core.container import register_routers
from app.core.database import engine, init_db
from app.core.redis_client import close_redis, init_redis

AsyncCallable = Callable[[], Awaitable[None]]
RouterRegistrar = Callable[[FastAPI], None]
logger = logging.getLogger(__name__)


def configure_middlewares(app: FastAPI, settings: Settings) -> None:
    allowed_origins = list(settings.CORS_ORIGINS)
    # file:// pages send Origin: null; allow it for local integration pages.
    if "null" not in allowed_origins:
        allowed_origins.append("null")

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


def build_lifespan(
    *,
    database_initializer: AsyncCallable,
    redis_initializer: AsyncCallable,
    redis_closer: AsyncCallable,
    database_engine: Any,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_initialized = False
        redis_initialized = False

        try:
            # 先尝试初始化数据库，失败不中断启动
            try:
                await database_initializer()
                db_initialized = True
            except Exception as e:
                print(f"Warning: Database initialization failed - {e}")
                print("Continuing without database...")

            # 尝试初始化 Redis，失败不中断启动
            try:
                await redis_initializer()
                redis_initialized = True
            except Exception as e:
                print(f"Warning: Redis initialization failed - {e}")
                print("Continuing without Redis...")

            yield
        finally:
            if redis_initialized:
                await redis_closer()
            if db_initialized:
                await database_engine.dispose()

    return lifespan


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
            database_initializer=database_initializer,
            redis_initializer=redis_initializer,
            redis_closer=redis_closer,
            database_engine=database_engine,
        ),
    )

    maybe_mount_frontend(app, app_settings)
    configure_middlewares(app, app_settings)
    app.middleware("http")(log_requests)
    router_registrar(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
