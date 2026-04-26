"""
Eko AI Agent 后端服务入口
基于 FastAPI 框架，提供 RESTful API 和 WebSocket 支持

主要功能：
- 会话管理与 Agent 执行
- RAG 知识库
- Canvas 白板协作
- 飞书集成（WebSocket 长连接）
"""
# TODO(PRD-2.1): move intent routing and scenario selection into backend/app/modules/intent.
# TODO(PRD-2.0): add login/session auth routes under backend/app/api/auth.py and backend/app/modules/auth.
# TODO(PRD-2.3): move workspace locking, creator permissions, and collaboration state into backend/app/modules/workspace.
# TODO(PRD-4.4): move Redis Pub/Sub and realtime broadcast into backend/app/modules/sync.
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import init_db, engine
from app.core.redis_client import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await init_redis()
    yield
    # Shutdown
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Static files for frontend test page
import os
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")

generated_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated")
os.makedirs(generated_path, exist_ok=True)
app.mount("/generated", StaticFiles(directory=generated_path), name="generated")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request logging
@app.middleware("http")
async def log_requests(request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response


# Health check
@app.get("/system/ping")
async def ping():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.utcnow()}


@app.get("/hello")
async def hello():
    return {"message": "Hello World"}


from sqlalchemy import text


@app.get("/system/check-db")
async def check_db():
    from app.core.database import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "postgres": "connected"}
    except Exception as e:
        return {"status": "error", "postgres": str(e)}


@app.get("/system/check-redis")
async def check_redis():
    from app.core.redis_client import get_redis
    try:
        r = await get_redis()
        await r.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        return {"status": "error", "redis": str(e)}


# Import and register routers
from app.api import sessions, rag, agent, canvas, settings as settings_router, webhook, ppt, ppt_templates, auth

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(canvas.router, prefix="/api/v1/canvas", tags=["canvas"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(webhook.router, prefix="/api/v1/webhook", tags=["webhook"])
app.include_router(ppt.router, prefix="/api/v1/ppt", tags=["ppt"])
app.include_router(ppt_templates.router, prefix="/api/v1/ppt/templates", tags=["ppt-templates"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
