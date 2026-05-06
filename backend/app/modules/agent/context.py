from __future__ import annotations

from typing import Any

from app.modules.agent.schemas import AgentChatRequest, AgentContext, ChatMessage


class AgentContextAssembler:
    """Builds the durable context for one Agent turn.

    Inspired by coding agents such as opencode, the backend owns context
    recovery instead of relying on the UI to resend a perfect transcript.
    """

    def __init__(self, max_chat_history: int = 60) -> None:
        self._max_chat_history = max_chat_history

    async def assemble(self, request: AgentChatRequest, *, sync_service: Any | None = None) -> AgentChatRequest:
        base = request.context or AgentContext()
        chat_history: list[ChatMessage] = []

        session = await self._get_sync_session(request.session_id, sync_service)
        if session is not None:
            chat_history.extend(self._coerce_messages(getattr(session, "context_messages", None)))
            chat_history.extend(self._coerce_messages(getattr(session, "messages", None)))

        chat_history.extend(base.chat_history)
        chat_history.append(ChatMessage(role="user", content=request.message))

        context = AgentContext(
            chat_history=self._dedupe_messages(chat_history)[-self._max_chat_history :],
            knowledge_docs=base.knowledge_docs,
            bitable_records=base.bitable_records,
        )
        return request.model_copy(update={"context": context})

    async def _get_sync_session(self, session_id: str, sync_service: Any | None) -> Any | None:
        if sync_service is None or not hasattr(sync_service, "get_session"):
            return None
        try:
            return await sync_service.get_session(session_id)
        except Exception:  # noqa: BLE001
            return None

    def _coerce_messages(self, raw_messages: Any) -> list[ChatMessage]:
        if not isinstance(raw_messages, list):
            return []
        messages: list[ChatMessage] = []
        for raw in raw_messages:
            payload = self._coerce_message_dict(raw)
            role = str(payload.get("role") or "").strip()
            content = str(payload.get("content") or "").strip()
            if not role or not content:
                continue
            messages.append(
                ChatMessage(
                    role=role,
                    content=content,
                    timestamp=self._coerce_int(payload.get("timestamp")),
                    sender_open_id=self._coerce_optional_str(payload.get("sender_open_id")),
                    sender_union_id=self._coerce_optional_str(payload.get("sender_union_id")),
                    sender_name=self._coerce_optional_str(payload.get("sender_name")),
                    platform_user_id=self._coerce_optional_str(payload.get("platform_user_id")),
                    platform_display_name=self._coerce_optional_str(payload.get("platform_display_name")),
                    avatar_url=self._coerce_optional_str(payload.get("avatar_url")),
                )
            )
        return messages

    def _coerce_message_dict(self, message: Any) -> dict[str, Any]:
        if isinstance(message, dict):
            return dict(message)
        if hasattr(message, "model_dump"):
            dumped = message.model_dump()
            return dumped if isinstance(dumped, dict) else {}
        return {
            "role": getattr(message, "role", None),
            "content": getattr(message, "content", None),
            "timestamp": getattr(message, "timestamp", None),
            "sender_open_id": getattr(message, "sender_open_id", None),
            "sender_union_id": getattr(message, "sender_union_id", None),
            "sender_name": getattr(message, "sender_name", None),
            "platform_user_id": getattr(message, "platform_user_id", None),
            "platform_display_name": getattr(message, "platform_display_name", None),
            "avatar_url": getattr(message, "avatar_url", None),
        }

    def _dedupe_messages(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        seen: set[tuple[str, str, int | None]] = set()
        deduped: list[ChatMessage] = []
        for message in messages:
            content = message.content.strip()
            if not content:
                continue
            key = (message.role.lower(), content, message.timestamp)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(message.model_copy(update={"content": content}))
        return deduped

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _coerce_optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
