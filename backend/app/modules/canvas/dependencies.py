from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService
from app.modules.feishu.board_client import FeishuBoardClient
from app.services.board_generate_service import BoardGenerateService

_canvas_repository = CanvasRepository()
_board_generate_service = BoardGenerateService(feishu_board_client=FeishuBoardClient())
_canvas_service = CanvasService(
    repository=_canvas_repository,
    board_generate_service=_board_generate_service,
)


def get_canvas_repository() -> CanvasRepository:
    return _canvas_repository


def get_canvas_service() -> CanvasService:
    return _canvas_service
