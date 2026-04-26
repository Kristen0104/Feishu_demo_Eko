"""
API Schema 定义模块
定义所有 API 请求/响应数据结构，用于 FastAPI 参数验证和数据序列化
"""
# TODO(PRD-2.2): add explicit schemas for Feishu card payloads, Bitable rows, and RAG retrieval results.
# TODO(PRD-2.3): add workspace permission, creator identity, and lock-state schemas.
# TODO(PRD-2.5): add realtime sync event schemas for multi-device collaboration.
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class IntentType(str, Enum):
    """用户意图类型枚举"""
    CHAT = "CHAT"
    DOC = "DOC"
    PPT = "PPT"
    SUMMARY = "SUMMARY"


# --- Session ---
class SessionBase(BaseModel):
    title: Optional[str] = None
    is_pinned: bool = False


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    clear_context: Optional[bool] = False


class SessionResponse(SessionBase):
    id: str
    user_id: str
    last_intent: Optional[IntentType] = None
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int
    page: int
    page_size: int


# --- RAG ---
class RagFileResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    created_at: datetime


class RagIngestRequest(BaseModel):
    url: Optional[str] = None
    knowledge_base: Optional[str] = None


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    session_id: Optional[str] = None


class RagSearchResult(BaseModel):
    content: str
    score: float
    file_id: str


# --- Agent ---
class AgentExecuteRequest(BaseModel):
    session_id: str
    message: str
    stream: bool = False


class AgentStopRequest(BaseModel):
    task_id: str


class TaskPlanStep(BaseModel):
    step: int
    action: str
    description: str


class TaskPlanResponse(BaseModel):
    task_id: str
    steps: list[TaskPlanStep]


class TaskHistoryItem(BaseModel):
    id: str
    message: str
    result: Optional[str] = None
    intent: IntentType
    created_at: datetime


# --- PPT ---
class PptPage(BaseModel):
    layout: str = "content"
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str | list[str]] = None
    body: Optional[str] = None
    notes: Optional[str | list[str]] = None
    footer: Optional[str] = None


class PptGenerateRequest(BaseModel):
    project_name: str = "aippt"
    pages: list[PptPage] = Field(..., min_length=1)
    template_name: Optional[str] = None
    template_dir: Optional[str] = None


class PptGenerateResponse(BaseModel):
    project_name: str
    project_path: str
    output_path: str
    result_url: str


class PptTemplateImportRequest(BaseModel):
    source_paths: list[str] = Field(..., min_length=1)
    collection_name: Optional[str] = None
    preferred_template: Optional[str] = None
    style_group: Optional[str] = None


class PptTemplatePackResponse(BaseModel):
    pack_dir: str
    source_pptx: str
    base_template: str
    manifest_path: str


class PptTemplateImportResponse(BaseModel):
    packs: list[PptTemplatePackResponse]


class PptTestRequest(BaseModel):
    chat_history: str = ""
    requirement: str
    ppt_mode: str = "fast"
    ppt_template: str = "auto"


class PptTestResponse(BaseModel):
    result: str
    result_url: Optional[str] = None
    slide_count: int
    generation_mode: str
    template_id: Optional[str] = None
    template_label: Optional[str] = None


# --- Canvas ---
class CanvasElementUpsert(BaseModel):
    id: str
    type: str
    data: dict


class CanvasSnapshotRequest(BaseModel):
    session_id: str


class CanvasUpdateRequest(BaseModel):
    session_id: str
    upsert: list[CanvasElementUpsert] = []
    delete: list[str] = []


class CanvasElementResponse(BaseModel):
    id: str
    type: str
    data: dict
    version: int


class CanvasResponse(BaseModel):
    session_id: str
    elements: list[CanvasElementResponse]
    version: int


class CanvasVersionResponse(BaseModel):
    version: int
    created_at: datetime
    snapshot: Optional[dict] = None


# --- WebSocket Payloads ---
class WSIntentRecognized(BaseModel):
    type: str = "INTENT_RECOGNIZED"
    intent: IntentType


class WSAgentPlanning(BaseModel):
    type: str = "AGENT_PLANNING"
    steps: list[dict]


class WSDocStream(BaseModel):
    type: str = "DOC_STREAM"
    chunk: str


class WSCanvasUpdate(BaseModel):
    type: str = "CANVAS_UPDATE"
    upsert: list[dict]
    delete: list[str]


class WSTaskCompleted(BaseModel):
    type: str = "TASK_COMPLETED"
    result_url: Optional[str] = None
    bitable_id: Optional[str] = None


class WSCursorSync(BaseModel):
    type: str = "CURSOR_SYNC"
    user_id: str
    x: float
    y: float


# --- Settings ---
class BitableConfigRequest(BaseModel):
    app_token: str
    table_id: str


class BitableTableResponse(BaseModel):
    table_id: str
    name: str


class BitableFieldResponse(BaseModel):
    field_id: str
    field_name: str
    field_type: str


# --- System ---
class PingResponse(BaseModel):
    status: str
    timestamp: datetime


# --- Auth ---
class FeishuLoginRequest(BaseModel):
    feishu_open_id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class AuthUserResponse(BaseModel):
    id: str
    feishu_open_id: Optional[str] = None
    name: str
    avatar_url: Optional[str] = None


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: AuthUserResponse


class AuthMeResponse(BaseModel):
    user: AuthUserResponse
