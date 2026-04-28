from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PptTaskCreateRequest(BaseModel):
    topic: str
    prompt: str
    title: str | None = None


class PptTaskLogSchema(BaseModel):
    step: str
    message: str


class PptTaskSchema(BaseModel):
    task_id: str
    topic: str
    prompt: str
    title: str | None = None
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"
    current_step: Literal["pending", "generating", "validating", "saving", "succeeded", "failed"] = "pending"
    artifact_kind: Literal["html"] = "html"
    preview_url: str | None = None
    artifact_path: str | None = None
    pptx_status: Literal["pending", "running", "succeeded", "failed"] = "pending"
    pptx_current_step: Literal["pending", "exporting", "succeeded", "failed"] = "pending"
    pptx_path: str | None = None
    pptx_download_url: str | None = None
    pptx_error_message: str | None = None
    error_message: str | None = None
    logs: list[PptTaskLogSchema] = Field(default_factory=list)
