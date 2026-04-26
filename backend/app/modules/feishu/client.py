from __future__ import annotations

from app.modules.feishu.schemas import FeishuCardSchema


class FeishuClient:
    # Platform API wiring will live here once the module stops being a stub.
    def get_card(self, card_id: str) -> FeishuCardSchema:
        return FeishuCardSchema(
            card_id=card_id,
            title="Stub Feishu Card",
            platform="feishu",
        )
