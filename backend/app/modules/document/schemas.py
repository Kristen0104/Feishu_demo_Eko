from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    REPORT = "report"
    PLAN = "plan"
    MINUTES = "minutes"
    PROPOSAL = "proposal"
    GENERAL = "general"


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


class DocumentGenerationRequest(BaseModel):
    session_id: str
    topic: str
    requirement: str
    document_type: DocumentType = DocumentType.GENERAL
    tone: str = "formal"
    chat_history: list[ChatMessage] = Field(default_factory=list)
    knowledge_docs: list[KnowledgeDoc] = Field(default_factory=list)
    bitable_records: list[BitableRecord] = Field(default_factory=list)


class DocumentEditRequest(BaseModel):
    session_id: str
    instruction: str
    current_content: str
    title: str | None = None


class DocumentEditResponse(BaseModel):
    session_id: str
    status: str
    content: str
    summary: str


class DocumentGenerationResponse(BaseModel):
    session_id: str
    status: str
    content: str


class DocumentSaveRequest(BaseModel):
    session_id: str
    title: str
    content: str
    sync_to_feishu: bool = False
    app_token: str | None = None
    table_id: str | None = None


class DocumentSaveResponse(BaseModel):
    session_id: str
    status: str
    message: str


class DocumentAutoSyncRequest(BaseModel):
    session_id: str
    title: str
    content: str
    current_url: str | None = None


class DocumentAutoSyncResponse(BaseModel):
    session_id: str
    status: str
    message: str
    document_url: str | None = None
