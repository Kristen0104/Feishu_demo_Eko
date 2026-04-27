from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.core import container
from app.modules.canvas.ai_service import HttpCanvasAiService
from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService


def create_real_feishu_app() -> FastAPI:
    app = FastAPI(title="Canvas Real Feishu Dev Server")
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    container.register_routers(app)

    canvas_service = CanvasService(
        repository=CanvasRepository(storage_dir=BACKEND_ROOT / "runtime" / "canvas-real"),
        ai_service=HttpCanvasAiService(settings=settings),
    )
    app.dependency_overrides[get_canvas_service] = lambda: canvas_service
    return app


app = create_real_feishu_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
