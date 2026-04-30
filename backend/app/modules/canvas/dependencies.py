from __future__ import annotations

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService
from app.modules.feishu.board_client import FeishuBoardClient
from app.services.board_generate_service import BoardGenerateService

_canvas_repository: CanvasRepository | None = None
_board_generate_service: BoardGenerateService | None = None
_canvas_service: CanvasService | None = None


def get_canvas_repository() -> CanvasRepository:
    global _canvas_repository
    if _canvas_repository is None:
        _canvas_repository = CanvasRepository()
    return _canvas_repository


def get_board_generate_service() -> BoardGenerateService:
    global _board_generate_service
    if _board_generate_service is None:
        _board_generate_service = BoardGenerateService(feishu_board_client=FeishuBoardClient())
    return _board_generate_service


def get_canvas_service() -> CanvasService:
    global _canvas_service
    if _canvas_service is None:
        _canvas_service = CanvasService(
            repository=get_canvas_repository(),
            board_generate_service=get_board_generate_service(),
        )
    return _canvas_service


def reset_canvas_dependencies() -> None:
    global _canvas_repository, _board_generate_service, _canvas_service
    _canvas_repository = None
    _board_generate_service = None
    _canvas_service = None
