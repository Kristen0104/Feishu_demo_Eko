from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CanvasSessionSchema(BaseModel):
    session_id: str
    title: str
    mode: Literal["canvas"] = "canvas"


class CanvasBoardTaskCreateRequest(BaseModel):
    message: str
    sharing_url: str
    whiteboard_id: str | None = None
    title: str | None = None
    replace_existing: bool = False


class CanvasBoardTaskLogSchema(BaseModel):
    step: str
    message: str


class CanvasBoardTaskSchema(BaseModel):
    task_id: str
    message: str
    sharing_url: str
    title: str | None = None
    status: Literal["pending", "running", "succeeded", "failed"] = "pending"
    current_step: Literal[
        "pending",
        "resolving_target",
        "planning",
        "rendering",
        "exporting_preview",
        "succeeded",
        "failed",
    ] = "pending"
    render_mode: Literal["import_diagram", "create_notes"]
    whiteboard_id: str | None = None
    preview_url: str | None = None
    ticket_id: str | None = None
    node_ids: list[str] = Field(default_factory=list)
    deleted_count: int = 0
    error_message: str | None = None
    result_summary: str | None = None
    logs: list[CanvasBoardTaskLogSchema] = Field(default_factory=list)
