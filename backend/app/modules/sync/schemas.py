from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SyncChannelSchema(BaseModel):
    session_id: str
    transport: Literal["websocket"] = "websocket"


class SyncContextMessageSchema(BaseModel):
    role: str
    content: str
    timestamp: int | None = None
    sender_open_id: str | None = None
    sender_union_id: str | None = None
    sender_name: str | None = None
    platform_user_id: str | None = None
    platform_display_name: str | None = None
    avatar_url: str | None = None


class SyncSessionMessageSchema(BaseModel):
    role: str
    content: str
    timestamp: int | None = None
    sender_open_id: str | None = None
    sender_union_id: str | None = None
    sender_name: str | None = None
    platform_user_id: str | None = None
    platform_display_name: str | None = None
    avatar_url: str | None = None


class SyncSessionSchema(BaseModel):
    session_id: str
    source: str
    title: str
    summary: str
    status: str
    user_id: str | None = None
    opened_at: str
    updated_at: str
    chat_id: str | None = None
    message_id: str | None = None
    context_size: int = 0
    instruction: str | None = None
    intent: str | None = None
    artifact: dict[str, Any] | None = None
    context_messages: list[SyncContextMessageSchema] = Field(default_factory=list)
    selected_context_messages: list[SyncContextMessageSchema] = Field(default_factory=list)
    messages: list[SyncSessionMessageSchema] = Field(default_factory=list)
    collaborator_user_ids: list[str] = Field(default_factory=list)
    collaborator_emails: list[str] = Field(default_factory=list)


class SyncContextSelectionRequest(BaseModel):
    start_index: int = Field(ge=0)
    end_index: int = Field(ge=0)
    skip_context: bool = False
