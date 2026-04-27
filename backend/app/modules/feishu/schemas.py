from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FeishuCardSchema(BaseModel):
    card_id: str
    title: str
    platform: str


class FeishuDocumentResolveRequestSchema(BaseModel):
    share_url: str


class FeishuDocumentWhiteboardImportRequestSchema(BaseModel):
    share_url: str
    session_id: str


class FeishuDocumentContentSchema(BaseModel):
    document_token: str
    document_id: str
    title: str
    plain_text: str
    raw_content: dict[str, Any] = Field(default_factory=dict)
    share_url: str


class FeishuDocumentBlockSchema(BaseModel):
    block_id: str
    block_type: int
    raw_block: dict[str, Any] = Field(default_factory=dict)


class FeishuDocumentWhiteboardSchema(BaseModel):
    whiteboard_id: str
    block_id: str


class FeishuDocumentBlocksSchema(BaseModel):
    document_id: str
    blocks: list[FeishuDocumentBlockSchema] = Field(default_factory=list)
    whiteboards: list[FeishuDocumentWhiteboardSchema] = Field(default_factory=list)


class FeishuWhiteboardNodesSchema(BaseModel):
    whiteboard_id: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class FeishuDocumentWhiteboardNodesSchema(BaseModel):
    document_id: str
    whiteboard_id: str
    block_id: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class FeishuDocumentWhiteboardsDiscoverySchema(BaseModel):
    document_id: str
    document_token: str
    title: str
    whiteboards: list[FeishuDocumentWhiteboardSchema] = Field(default_factory=list)


class FeishuBoardElementMappingSchema(BaseModel):
    source_element_id: str
    working_element_id: str
    element_type: Literal["node", "edge"]
    origin_type: Literal["source_import", "ai", "user", "merge"] = "source_import"
    mapping_status: Literal["active", "detached", "conflicted"] = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeishuBoardSourceSchema(BaseModel):
    board_id: str
    title: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeishuBoardWorkingSchema(BaseModel):
    working_board_id: str
    session_id: str
    latest_version: int
    crdt_document: dict[str, Any] = Field(default_factory=dict)
    latest_snapshot: dict[str, Any] = Field(default_factory=dict)
    offline_state: Literal["clean", "dirty", "replaying"] = "clean"


class FeishuBoardAdapterPayloadSchema(BaseModel):
    session_id: str
    source_board: FeishuBoardSourceSchema
    working_board: FeishuBoardWorkingSchema | None = None
    element_mappings: list[FeishuBoardElementMappingSchema] = Field(default_factory=list)


class FeishuBoardPublishResultSchema(BaseModel):
    mode: Literal["adapter_only", "upstream"]
    accepted: bool = True
    session_id: str
    board_id: str
    exported_board: FeishuBoardAdapterPayloadSchema
    upstream_payload: dict[str, Any] = Field(default_factory=dict)


class FeishuBoardSyntaxImportRequestSchema(BaseModel):
    code: str
    syntax_type: int
    style_type: int = 1
    diagram_type: int = 0


class FeishuBoardSyntaxImportResultSchema(BaseModel):
    mode: Literal["adapter_only", "upstream"]
    accepted: bool = True
    board_id: str
    upstream_payload: dict[str, Any] = Field(default_factory=dict)


class FeishuBoardMermaidImportRequestSchema(BaseModel):
    code: str
    syntax_type: int = 2
    style_type: int = 1
    diagram_type: int = 0
