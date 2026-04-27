from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.feishu.schemas import FeishuBoardElementMappingSchema
from app.modules.feishu.schemas import FeishuBoardAdapterPayloadSchema
from app.modules.feishu.schemas import FeishuBoardPublishResultSchema
from app.modules.feishu.schemas import FeishuBoardMermaidImportRequestSchema


class CanvasSessionSchema(BaseModel):
    session_id: str
    title: str
    mode: Literal["canvas"] = "canvas"


class BoardSessionSchema(BaseModel):
    session_id: str
    title: str
    mode: Literal["canvas"] = "canvas"
    owner_user_id: str
    collaborator_ids: list[str] = Field(default_factory=list)
    permission_mode: Literal["creator_only", "collaborative", "viewer_only"]
    sync_state: Literal["idle", "syncing", "conflict"]
    offline_capability: Literal["disabled", "single_user_only"]


class FeishuSourceBoardSchema(BaseModel):
    source_board_id: str
    session_id: str
    source_version: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    sync_cursor: str | None = None


class EkoWorkingBoardSchema(BaseModel):
    working_board_id: str
    session_id: str
    latest_version: int
    crdt_document: dict[str, Any] = Field(default_factory=dict)
    latest_snapshot: dict[str, Any] = Field(default_factory=dict)
    offline_state: Literal["clean", "dirty", "replaying"] = "clean"


class BoardChangeSchema(BaseModel):
    change_id: str
    session_id: str
    change_type: Literal[
        "user_edit",
        "ai_patch",
        "source_import",
        "sync_export",
        "conflict_detected",
        "merge_resolved",
        "offline_replay",
    ]
    actor_type: Literal["user", "ai", "system", "feishu"]
    actor_id: str | None = None
    target_scope: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    base_version: str | None = None
    result_version: str | None = None


class CanvasSessionDetailSchema(BaseModel):
    session: BoardSessionSchema
    source_board: FeishuSourceBoardSchema
    working_board: EkoWorkingBoardSchema
    element_mappings: list[FeishuBoardElementMappingSchema] = Field(default_factory=list)
    recent_changes: list[BoardChangeSchema] = Field(default_factory=list)
    merge_reviews: list["MergeReviewSchema"] = Field(default_factory=list)


class CanvasGenerationRequestSchema(BaseModel):
    generation_mode: Literal["full_board", "targeted_patch"]
    chat_context: list[dict[str, str]] = Field(default_factory=list)
    user_prompt: str
    board_context: dict[str, Any] = Field(default_factory=dict)
    session_metadata: dict[str, Any] = Field(default_factory=dict)
    selection_context: dict[str, Any] | None = None


class GenerationInfoSchema(BaseModel):
    source: Literal["ai"]
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None


class BoardPatchSchema(BaseModel):
    generation_mode: Literal["full_board", "targeted_patch"]
    patch_id: str
    operations: list[dict[str, Any]] = Field(default_factory=list)
    summary: str
    style_plan: dict[str, Any] | None = None
    full_board: dict[str, Any] | None = None
    targeted_patch: dict[str, Any] | None = None
    generation_info: GenerationInfoSchema | None = None


class MergeReviewRequestSchema(BaseModel):
    source_version: str
    working_version: int
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class MergeReviewSchema(BaseModel):
    review_id: str
    session_id: str
    source_version: str | None = None
    working_version: int | None = None
    status: Literal["pending_review", "partially_resolved", "resolved"] = "pending_review"
    summary: dict[str, int] = Field(default_factory=dict)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)


class MergeResolutionItemSchema(BaseModel):
    working_element_id: str
    resolution: Literal["source", "working"]


class MergeResolutionRequestSchema(BaseModel):
    review_id: str
    actor_id: str | None = None
    resolutions: list[MergeResolutionItemSchema] = Field(default_factory=list)


class CanvasRefreshReviewSchema(BaseModel):
    detail: CanvasSessionDetailSchema
    merge_review: MergeReviewSchema | None = None


class CanvasExportRequestSchema(BaseModel):
    allow_conflicted_export: bool = False


class CanvasExportResultSchema(BaseModel):
    export_status: Literal["exported", "exported_with_conflicts"]
    exported_board: FeishuBoardAdapterPayloadSchema
    detail: CanvasSessionDetailSchema


class CanvasPublishResultSchema(BaseModel):
    export_status: Literal["exported", "exported_with_conflicts"]
    publish_result: FeishuBoardPublishResultSchema
    detail: CanvasSessionDetailSchema


class CanvasMermaidImportResultSchema(BaseModel):
    detail: CanvasSessionDetailSchema


class CanvasMermaidImportRequestSchema(FeishuBoardMermaidImportRequestSchema):
    pass
