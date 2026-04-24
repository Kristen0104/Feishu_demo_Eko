"""
API Schema 定义模块
定义所有 API 请求/响应数据结构，用于 FastAPI 参数验证和数据序列化
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class IntentType(str, Enum):
    """用户意图类型枚举"""
    """用户意图类型枚举"""
    CHAT = "CHAT"
    DOC = "DOC"
    PPT = "PPT"
    SUMMARY = "SUMMARY"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str] = None
    feishu_open_id: Optional[str] = None


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
