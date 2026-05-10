from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RagFileSchema(BaseModel):
    file_id: str
    filename: str
    source: str
    chunk_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class RagFileCreateRequest(BaseModel):
    filename: str
    source: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagSearchResultSchema(BaseModel):
    chunk_id: str
    source_id: str
    source_type: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagSearchResponse(BaseModel):
    query: str
    results: list[RagSearchResultSchema]
