from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.modules.canvas.ai_service import HttpCanvasAiService
from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService


@lru_cache(maxsize=1)
def get_canvas_repository() -> CanvasRepository:
    return CanvasRepository()


@lru_cache(maxsize=1)
def get_canvas_ai_service() -> HttpCanvasAiService:
    return HttpCanvasAiService(settings=get_settings())


def get_canvas_service() -> CanvasService:
    return CanvasService(
        repository=get_canvas_repository(),
        ai_service=get_canvas_ai_service(),
    )
