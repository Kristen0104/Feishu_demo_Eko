from __future__ import annotations

from app.modules.feishu.client import FeishuClient
from app.modules.feishu.service import FeishuService


def get_feishu_client() -> FeishuClient:
    return FeishuClient()


def get_feishu_service() -> FeishuService:
    return FeishuService(client=get_feishu_client())
