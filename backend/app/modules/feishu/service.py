from __future__ import annotations

from app.modules.feishu.client import FeishuClient
from app.modules.feishu.schemas import FeishuCardSchema


class FeishuService:
    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return self._client.get_card(card_id)
