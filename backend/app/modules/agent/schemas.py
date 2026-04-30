from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


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


class AgentChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1)
    sharing_url: str | None = None


class AgentChatArtifact(BaseModel):
    kind: Literal["docx", "ppt", "board"]
    content: str | None = None
    deck_id: str | None = None
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
    error: str | None = None
