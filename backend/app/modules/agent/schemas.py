from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentIntent(str, Enum):
    UNKNOWN = "unknown"
    CHAT = "chat"
    DOCX = "docx"
    PPT = "ppt"
    BOARD = "board"
    DOCUMENT = "document"
    PRESENTATION = "presentation"


class SubagentType(str, Enum):
    ROUTER = "router"
    COLLECTOR = "collector"
    WRITER = "writer"
    SYNC = "sync"


class AgentStatus(str, Enum):
    PENDING = "pending"
    ROUTING = "routing"
    COLLECTING = "collecting"
    WRITING = "writing"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: int | None = None
    sender_open_id: str | None = None
    sender_union_id: str | None = None
    sender_name: str | None = None
    platform_user_id: str | None = None
    platform_display_name: str | None = None
    avatar_url: str | None = None


class KnowledgeDoc(BaseModel):
    title: str
    content: str
    source: str | None = None


class BitableRecord(BaseModel):
    table_name: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class AgentContext(BaseModel):
    chat_history: list[ChatMessage] = Field(default_factory=list)
    knowledge_docs: list[KnowledgeDoc] = Field(default_factory=list)
    bitable_records: list[BitableRecord] = Field(default_factory=list)


class AgentRequest(BaseModel):
    session_id: str
    instruction: str
    style: str = "formal"
    context: AgentContext | None = None


class AgentResponse(BaseModel):
    session_id: str
    status: AgentStatus
    intent: AgentIntent = AgentIntent.UNKNOWN
    message: str
    content: str | None = None
    error: str | None = None


class SyncDocumentRequest(BaseModel):
    session_id: str
    title: str
    content: str
    app_token: str | None = None
    table_id: str | None = None


class SyncDocumentResponse(BaseModel):
    session_id: str
    status: AgentStatus
    message: str
    document_url: str | None = None
    record_id: str | None = None
    error: str | None = None


class AgentTaskSchema(BaseModel):
    task_id: str
    status: Literal["accepted"] = "accepted"


class AgentPlanFinalOutput(BaseModel):
    format: str
    requirements: list[str] = Field(default_factory=list)


class AgentPlanStep(BaseModel):
    id: str
    title: str
    description: str
    type: Literal["reasoning", "tool_call", "generation", "validation", "clarification"]
    status: Literal["pending", "in_progress", "completed", "blocked", "failed"] = "pending"
    tool: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    expected_output: str
    depends_on: list[str] = Field(default_factory=list)


class AgentTaskPlan(BaseModel):
    goal: str
    intent: str
    task_complexity: Literal["simple", "medium", "complex"] = "medium"
    missing_info: list[str] = Field(default_factory=list)
    requires_context_selection: bool = False
    need_clarification: bool = False
    questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    summary: str
    visible_summary: str | None = None
    tool_candidates: list[str] = Field(default_factory=list)
    steps: list[AgentPlanStep] = Field(default_factory=list)
    final_output: AgentPlanFinalOutput
    clarification_needed: bool = False
    clarification_question: str | None = None


class AgentRetrievedContext(BaseModel):
    source_id: str
    source_type: str
    title: str
    content: str
    score: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTraceEvent(BaseModel):
    type: str
    status: Literal["pending", "in_progress", "completed", "blocked", "failed"] = "completed"
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentEventV1(BaseModel):
    event: Literal[
        "turn.started",
        "intent.recognized",
        "context.loaded",
        "retrieval.started",
        "retrieval.completed",
        "source.bitable.started",
        "source.bitable.completed",
        "source.bitable.empty",
        "source.bitable.failed",
        "plan.created",
        "plan.summary",
        "plan.step",
        "tool.selected",
        "tool.started",
        "tool.completed",
        "clarification.requested",
        "artifact.archived",
        "artifact.archive_failed",
        "result.created",
        "turn.failed",
    ]
    status: Literal["pending", "running", "completed", "blocked", "failed"] = "completed"
    channel: Literal["chat", "status", "plan", "sources", "artifact", "log", "error"] = "log"
    visibility: Literal["user", "detail", "debug"] = "detail"
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1)
    sharing_url: str | None = None
    current_document: AgentChatArtifact | None = None
    context: AgentContext | None = None
    sender: dict[str, Any] | None = None
    planning_enabled: bool = True


class AgentChatArtifact(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["docx", "ppt", "board"]
    content: str | None = None
    job_id: str | None = None
    download_url: str | None = None
    progress: int | None = None
    current_step: str | None = None
    task_id: str | None = None
    status: str | None = None
    whiteboard_id: str | None = None
    sharing_url: str | None = None
    result_summary: str | None = None
    error_message: str | None = None


class AgentChatResponse(BaseModel):
    session_id: str
    intent: Literal["chat", "docx", "ppt", "board"]
    status: Literal["completed", "failed"]
    message: str
    artifact: AgentChatArtifact | None = None
    plan: AgentTaskPlan | None = None
    events: list[AgentEventV1] = Field(default_factory=list)
    error: str | None = None
