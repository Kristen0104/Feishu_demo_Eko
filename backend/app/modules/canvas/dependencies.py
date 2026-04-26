from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService


def get_canvas_repository() -> CanvasRepository:
    return CanvasRepository()


def get_canvas_service() -> CanvasService:
    return CanvasService(repository=get_canvas_repository())
