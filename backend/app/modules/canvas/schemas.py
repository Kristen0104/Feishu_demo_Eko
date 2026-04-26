from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CanvasSessionSchema(BaseModel):
    session_id: str
    title: str
    mode: Literal["canvas"] = "canvas"
