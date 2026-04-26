from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SyncChannelSchema(BaseModel):
    session_id: str
    transport: Literal["websocket"] = "websocket"
