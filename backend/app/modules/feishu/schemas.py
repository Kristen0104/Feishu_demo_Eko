from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FeishuCardSchema(BaseModel):
    card_id: str
    title: str
    platform: str


class PublishToFeishuRequest(BaseModel):
    session_id: str
    title: str
    markdown_content: str
    app_token: str | None = None
    table_id: str | None = None


class PublishToFeishuResponse(BaseModel):
    ticket: str
    status: Literal["processing", "success", "failed"] = "processing"


class ImportTaskStatus(BaseModel):
    ticket: str
    status: Literal["processing", "success", "failed"]
    document_url: str | None = None


class FeishuBoardImportRequest(BaseModel):
    whiteboard_id: str
    source: str
    source_type: Literal["file", "content"] = "file"
    syntax: Literal["plantuml", "mermaid"] = "plantuml"
    diagram_type: str = "auto"
    style: Literal["board", "classic"] = "board"
    user_access_token: str | None = None


class FeishuBoardImportSchema(BaseModel):
    whiteboard_id: str
    ticket_id: str
    syntax: str
    syntax_type: int
    style: str
    style_type: int
    diagram_type: str
    diagram_type_value: int


class FeishuBoardCreateNotesRequest(BaseModel):
    whiteboard_id: str
    nodes: list[dict[str, Any]] | None = None
    nodes_json: str | None = None
    source_type: Literal["file", "content"] = "file"
    client_token: str = ""
    user_id_type: str = "open_id"
    user_access_token: str | None = None


class FeishuBoardCreateNotesSchema(BaseModel):
    whiteboard_id: str
    node_ids: list[str]
    count: int


class FeishuBoardNodesSchema(BaseModel):
    nodes: dict[str, dict[str, Any]] | list[dict[str, Any]] = Field(default_factory=dict)


class FeishuBoardImageSchema(BaseModel):
    whiteboard_id: str
    preview_url: str


class FeishuBoardUpdateRequest(BaseModel):
    whiteboard_id: str
    nodes: list[dict[str, Any]] | None = None
    nodes_json: str | None = None
    source_type: Literal["file", "content"] = "file"
    overwrite: bool = False
    dry_run: bool = False
    user_access_token: str | None = None


class FeishuBoardUpdateSchema(BaseModel):
    whiteboard_id: str
    new_node_ids: list[str] = Field(default_factory=list)
    created_count: int = 0
    deleted_count: int = 0
    dry_run: bool = False
    existing_count: int | None = None


class FeishuBoardDeleteRequest(BaseModel):
    whiteboard_id: str
    node_ids: list[str] = Field(default_factory=list)
    all: bool = False
    user_access_token: str | None = None


class FeishuBoardDeleteSchema(BaseModel):
    whiteboard_id: str
    deleted_ids: list[str] = Field(default_factory=list)
    deleted_count: int = 0
