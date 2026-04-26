from __future__ import annotations

from pydantic import BaseModel


class RagFileSchema(BaseModel):
    file_id: str
    filename: str
    source: str
