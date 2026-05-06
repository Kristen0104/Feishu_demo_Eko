from __future__ import annotations

from app.modules.feishu.board_client import FeishuBoardClient
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.service import FeishuService

_feishu_board_client: FeishuBoardClient | None = None
_feishu_client: FeishuClient | None = None
_feishu_service: FeishuService | None = None


def get_feishu_board_client() -> FeishuBoardClient:
    global _feishu_board_client
    if _feishu_board_client is None:
        _feishu_board_client = FeishuBoardClient()
    return _feishu_board_client


def get_feishu_client() -> FeishuClient:
    global _feishu_client
    if _feishu_client is None:
        _feishu_client = FeishuClient(board_client=get_feishu_board_client())
    return _feishu_client


def get_feishu_service() -> FeishuService:
    global _feishu_service
    if _feishu_service is None:
        _feishu_service = FeishuService(client=get_feishu_client())
    return _feishu_service


def reset_feishu_dependencies() -> None:
    global _feishu_board_client, _feishu_client, _feishu_service
    _feishu_board_client = None
    _feishu_client = None
    _feishu_service = None
