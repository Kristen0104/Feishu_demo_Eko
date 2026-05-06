from __future__ import annotations

import time
from typing import Any

from fastapi import WebSocket

from app.modules.sync.manager import SessionRecord, SyncConnectionManager, get_sync_connection_manager
from app.modules.sync.schemas import SyncChannelSchema, SyncSessionSchema


class SyncService:
    def __init__(self, manager: SyncConnectionManager | None = None) -> None:
        self._manager = manager or get_sync_connection_manager()
        self._last_doc_stream_persist_at: dict[str, float] = {}

    def get_channel(self, session_id: str) -> SyncChannelSchema:
        return SyncChannelSchema(session_id=session_id)

    async def register_session(
        self,
        session_id: str,
        *,
        source: str,
        title: str,
        summary: str,
        status: str = "进行中",
        user_id: str | None = None,
        chat_id: str | None = None,
        message_id: str | None = None,
        context_size: int = 0,
        instruction: str | None = None,
        context_messages: list[dict[str, Any]] | None = None,
        intent: str | None = None,
        artifact: dict[str, Any] | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> SyncSessionSchema:
        record = await self._manager.register_session(
            session_id,
            source=source,
            title=title,
            summary=summary,
            status=status,
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            context_size=context_size,
            instruction=instruction,
            context_messages=context_messages,
            intent=intent,
            artifact=artifact,
            messages=messages,
        )
        return self._to_schema(record)

    async def list_sessions(self, user_id: str | None = None) -> list[SyncSessionSchema]:
        return [
            self._to_schema(record, compact_artifact=True)
            for record in await self._manager.list_sessions(user_id=user_id)
        ]

    async def get_session(self, session_id: str, user_id: str | None = None) -> SyncSessionSchema | None:
        record = await self._manager.get_session(session_id, user_id=user_id)
        return self._to_schema(record) if record is not None else None

    async def delete_session(self, session_id: str) -> bool:
        return await self._manager.delete_session(session_id)

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await self._manager.connect(session_id, websocket)

    async def emit(self, session_id: str, envelope: dict[str, Any]) -> None:
        await self._manager.emit(session_id, envelope)

    async def publish_session_opened(
        self,
        session_id: str,
        *,
        source: str,
        user_id: str | None = None,
        chat_id: str | None = None,
        message_id: str | None = None,
        context_size: int | None = None,
        instruction: str | None = None,
        context_messages: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"source": source}
        if user_id:
            payload["user_id"] = user_id
        if chat_id:
            payload["chat_id"] = chat_id
        if message_id:
            payload["message_id"] = message_id
        if context_size is not None:
            payload["context_size"] = context_size
        if context_messages is not None:
            payload["context_messages"] = context_messages
        await self.register_session(
            session_id,
            source=source,
            title="飞书群聊新会话",
            summary="收到 @机器人 消息，正在识别意图并启动任务。",
            status="进行中",
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            context_size=context_size or 0,
            instruction=instruction,
            context_messages=context_messages,
            messages=messages,
        )
        await self.emit(
            session_id,
            {
                "type": "SESSION_OPENED",
                "session_id": session_id,
                "payload": payload,
            },
        )

    async def publish_task_completed(
        self,
        session_id: str,
        *,
        intent: str,
        message: str,
        status: str,
        artifact: dict[str, Any] | None = None,
        messages: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "intent": intent,
            "status": status,
            "message": message,
        }
        if artifact is not None:
            payload["artifact"] = artifact
        if messages is not None:
            payload["messages"] = messages
        if error is not None:
            payload["error"] = error
        await self._manager.update_session(
            session_id,
            status=status,
            summary=message,
            intent=intent,
            artifact=artifact,
            messages=messages,
        )
        await self.emit(
            session_id,
            {
                "type": "TASK_COMPLETED",
                "session_id": session_id,
                "payload": payload,
            },
        )

    async def publish_agent_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        replace_last: bool = False,
    ) -> None:
        if not content.strip():
            return
        session = await self.get_session(session_id)
        messages = [
            message.model_dump() if hasattr(message, "model_dump") else dict(message)
            for message in (session.messages if session is not None else [])
        ]
        message = {
            "role": role,
            "content": content,
        }
        if messages and messages[-1].get("role") == role and messages[-1].get("content") == content:
            return
        if replace_last and messages and messages[-1].get("role") == role:
            messages[-1] = message
        else:
            messages.append(message)
        await self._manager.update_session(
            session_id,
            messages=messages,
            summary=content,
        )
        await self.emit(
            session_id,
            {
                "type": "AGENT_MESSAGE",
                "session_id": session_id,
                "payload": {**message, "replace_last": replace_last},
            },
        )

    async def publish_document_stream_chunk(
        self,
        session_id: str,
        *,
        content: str,
        chunk: str,
    ) -> None:
        await self.emit(
            session_id,
            {
                "type": "DOC_STREAM",
                "session_id": session_id,
                "payload": {"chunk": chunk, "content": content},
            },
        )
        now = time.monotonic()
        last_persist_at = self._last_doc_stream_persist_at.get(session_id, 0.0)
        if now - last_persist_at < 5.0:
            return

        self._last_doc_stream_persist_at[session_id] = now
        artifact = {
            "kind": "docx",
            "content": content,
            "status": "running",
            "current_step": "生成文档",
        }
        await self._manager.update_session(
            session_id,
            status="进行中",
            summary="文档生成中。",
            intent="docx",
            artifact=artifact,
        )

    async def mark_session_running(
        self,
        session_id: str,
        *,
        context_size: int,
    ) -> None:
        await self._manager.update_session(
            session_id,
            status="进行中",
            summary=f"已选择 {context_size} 条上下文，正在生成回复。",
            context_size=context_size,
        )

    async def update_session_context(
        self,
        session_id: str,
        *,
        context_size: int,
        context_messages: list[dict[str, Any]],
    ) -> None:
        await self._manager.update_session(
            session_id,
            context_size=context_size,
            context_messages=context_messages,
        )
        await self.emit(
            session_id,
            {
                "type": "CONTEXT_LOADED",
                "session_id": session_id,
                "payload": {
                    "context_size": context_size,
                    "context_messages": context_messages,
                },
            },
        )

    async def publish_error(self, session_id: str, message: str, error: str | None = None) -> None:
        payload: dict[str, Any] = {"message": message}
        if error is not None:
            payload["error"] = error
        await self.emit(
            session_id,
            {
                "type": "ERROR",
                "session_id": session_id,
                "payload": payload,
            },
        )
        await self._manager.update_session(
            session_id,
            status="失败",
            summary=message,
        )

    def _to_schema(self, record: SessionRecord | None, *, compact_artifact: bool = False) -> SyncSessionSchema:
        if record is None:  # pragma: no cover - defensive guard
            raise ValueError("session record is missing")
        artifact = self._compact_artifact(record.artifact) if compact_artifact else record.artifact
        return SyncSessionSchema(
            session_id=record.session_id,
            source=record.source,
            title=record.title,
            summary=record.summary,
            status=record.status,
            user_id=record.user_id,
            opened_at=record.opened_at,
            updated_at=record.updated_at,
            chat_id=record.chat_id,
            message_id=record.message_id,
            context_size=record.context_size,
            instruction=record.instruction,
            intent=record.intent,
            artifact=artifact,
            context_messages=record.context_messages or [],
            messages=record.messages or [],
        )

    def _compact_artifact(self, artifact: dict[str, Any] | None) -> dict[str, Any] | None:
        if artifact is None:
            return None
        compact = dict(artifact)
        content = compact.get("content")
        if isinstance(content, str) and content:
            compact["content_preview"] = content[:240]
            compact["content_length"] = len(content)
            compact.pop("content", None)
        return compact
