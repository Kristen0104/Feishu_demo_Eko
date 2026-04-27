from __future__ import annotations

from app.modules.feishu.board_client import FeishuBoardClient
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.service import FeishuService

_feishu_board_client = FeishuBoardClient()
_feishu_client = FeishuClient(board_client=_feishu_board_client)
_feishu_service = FeishuService(client=_feishu_client)


def get_feishu_client() -> FeishuClient:
    return _feishu_client


def get_feishu_service() -> FeishuService:
    return _feishu_service
