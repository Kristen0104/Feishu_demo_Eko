from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel


class BoardTarget(BaseModel):
    source_kind: Literal["whiteboard", "document"]
    whiteboard_id: str | None = None
    doc_token: str | None = None


def resolve_board_target_from_sharing_url(sharing_url: str) -> BoardTarget:
    parsed = urlparse(sharing_url)
    segments = [segment for segment in parsed.path.split("/") if segment]

    if "board" in segments and segments[-1]:
        return BoardTarget(
            source_kind="whiteboard",
            whiteboard_id=segments[-1],
        )

    if "docx" in segments and segments[-1]:
        return BoardTarget(
            source_kind="document",
            doc_token=segments[-1],
        )

    raise ValueError(f"Unsupported Feishu sharing url: {sharing_url}")
