from __future__ import annotations

from pydantic import BaseModel


class FeishuCardSchema(BaseModel):
    card_id: str
    title: str
    platform: str
