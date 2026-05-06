from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.config import settings
from app.core import redis_client as redis_module
from app.modules.agent.schemas import ChatMessage
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.schemas import (
    FeishuBoardCreateNotesRequest,
    FeishuBoardCreateNotesSchema,
    FeishuBoardDeleteRequest,
    FeishuBoardDeleteSchema,
    FeishuBoardImageSchema,
    FeishuBoardImportRequest,
    FeishuBoardImportSchema,
    FeishuBoardNodesSchema,
    FeishuBoardUpdateRequest,
    FeishuBoardUpdateSchema,
    FeishuCardSchema,
)

logger = logging.getLogger(__name__)
_MENTION_TAG_RE = re.compile(r"<at[^>]*>.*?</at>", re.IGNORECASE | re.DOTALL)


class FeishuService:
    def __init__(self, client: FeishuClient, redis_client: Any | None = None) -> None:
        self._client = client
        self._redis = redis_client

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return self._client.get_card(card_id)

    def import_diagram(self, payload: FeishuBoardImportRequest) -> FeishuBoardImportSchema:
        return self._client.import_diagram(payload)

    def create_notes(self, payload: FeishuBoardCreateNotesRequest) -> FeishuBoardCreateNotesSchema:
        return self._client.create_notes(payload)

    def get_board_nodes(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardNodesSchema:
        return self._client.get_board_nodes(whiteboard_id, user_access_token=user_access_token)

    def get_board_image(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardImageSchema:
        return self._client.get_board_image(whiteboard_id, user_access_token=user_access_token)

    def update_board(self, payload: FeishuBoardUpdateRequest) -> FeishuBoardUpdateSchema:
        return self._client.update_board(payload)

    def delete_board(self, payload: FeishuBoardDeleteRequest) -> FeishuBoardDeleteSchema:
        return self._client.delete_board(payload)

    async def create_board_document(self, title: str) -> dict[str, str]:
        if self._client is None:
            return {
                "document_id": "docx_stub",
                "whiteboard_id": "wbcn_stub",
                "sharing_url": "https://example.feishu.cn/docx/docx_stub",
            }
        return await asyncio.to_thread(self._client.create_board_document, title)

    async def add_docx_permission_for_chat(
        self,
        document_id: str,
        chat_id: str,
        *,
        perm: str = "edit",
    ) -> dict[str, Any]:
        if self._client is None:
            return {"member_id": chat_id, "perm": perm}
        return await asyncio.to_thread(
            self._client.add_docx_permission_for_chat,
            document_id,
            chat_id,
            perm=perm,
        )

    async def send_text_message_to_chat(self, chat_id: str, text: str) -> dict[str, Any]:
        if "已自动同步飞书文档" in text or "自动同步飞书文档" in text:
            return {"message_id": "suppressed-auto-sync-message"}
        if self._client is None:
            return {"message_id": "stub-message"}
        return await asyncio.to_thread(self._client.send_text_message_to_chat, chat_id, text)

    def get_recent_chat_messages(
        self,
        chat_id: str,
        *,
        before_time_ms: int | None = None,
        lookback_minutes: int = 120,
        gap_minutes: int = 15,
    ) -> list[ChatMessage]:
        raw_messages = self._client.list_recent_chat_messages(
            chat_id,
            before_time_ms=before_time_ms,
            lookback_minutes=lookback_minutes,
        )
        return self._select_recent_context(
            raw_messages,
            before_time_ms=before_time_ms,
            lookback_minutes=lookback_minutes,
            gap_minutes=gap_minutes,
        )

    def get_chat_context_candidates(
        self,
        chat_id: str,
        *,
        before_time_ms: int | None = None,
        lookback_minutes: int = 120,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        raw_messages = self._client.list_recent_chat_messages(
            chat_id,
            before_time_ms=before_time_ms,
            lookback_minutes=lookback_minutes,
            page_size=limit,
            max_pages=1,
        )
        candidates: list[dict[str, Any]] = []
        cutoff = before_time_ms or None
        window_start = cutoff - lookback_minutes * 60 * 1000 if cutoff is not None else None
        for raw in raw_messages:
            timestamp = self._coerce_timestamp(raw.get("create_time"))
            if timestamp is None:
                continue
            if cutoff is not None and timestamp >= cutoff:
                continue
            if window_start is not None and timestamp < window_start:
                continue
            content = self._extract_message_text(raw)
            if not content:
                continue
            candidates.append(
                {
                    "role": self._infer_role(raw.get("sender")),
                    "content": content,
                    "timestamp": timestamp,
                    **self._extract_sender_profile(raw.get("sender")),
                }
            )
        candidates.sort(key=lambda item: item["timestamp"])
        return candidates[-limit:]

    async def create_import_ticket(self, markdown_content: str, title: str) -> str:
        return await asyncio.to_thread(self._client.create_import_task, markdown_content, title)

    async def complete_import_task(
        self,
        ticket: str,
        title: str,
        app_token: str | None = None,
        table_id: str | None = None,
    ) -> dict[str, Any]:
        document_url = None
        for _ in range(30):
            result = await asyncio.to_thread(self._client.get_import_task_result, ticket)
            if result is not None:
                document_url = result["url"]
                break
            await asyncio.sleep(1)

        if document_url is None:
            raise RuntimeError("Import task timeout after 30 seconds")

        record_id = None
        if app_token and table_id:
            fields = {
                settings.FEISHU_BITABLE_FIELD_TITLE: title,
                settings.FEISHU_BITABLE_FIELD_URL: document_url,
            }
            try:
                record_id = await asyncio.to_thread(
                    self._client.create_bitable_record,
                    app_token,
                    table_id,
                    fields,
                )
            except Exception as exc:
                logger.warning("Create bitable record skipped: %s", exc)

        return {
            "ticket": ticket,
            "document_url": document_url,
            "record_id": record_id,
            "status": "success",
        }

    async def publish_markdown_to_feishu(
        self,
        title: str,
        markdown_content: str,
        app_token: str | None = None,
        table_id: str | None = None,
        ticket: str | None = None,
    ) -> dict[str, Any]:
        ticket = ticket or await self.create_import_ticket(markdown_content, title)
        return await self.complete_import_task(ticket, title, app_token, table_id)

    async def publish_markdown_background(
        self,
        session_id: str,
        title: str,
        markdown_content: str,
        app_token: str | None = None,
        table_id: str | None = None,
        ticket: str | None = None,
    ) -> None:
        try:
            result = await self.publish_markdown_to_feishu(
                title=title,
                markdown_content=markdown_content,
                app_token=app_token,
                table_id=table_id,
                ticket=ticket,
            )
            message = {
                "session_id": session_id,
                "status": "completed",
                "document_url": result["document_url"],
                "record_id": result["record_id"],
            }
        except Exception as exc:
            logger.error("Publish failed for session %s: %s", session_id, exc)
            message = {
                "session_id": session_id,
                "status": "failed",
                "error": str(exc),
            }
        await self._publish_status(session_id, message)

    def get_import_status(self, ticket: str) -> dict[str, Any]:
        return self._client.get_import_task_status(ticket)

    def _select_recent_context(
        self,
        messages: list[dict[str, Any]],
        *,
        before_time_ms: int | None,
        lookback_minutes: int,
        gap_minutes: int,
    ) -> list[ChatMessage]:
        cutoff = before_time_ms or None
        window_start = cutoff - lookback_minutes * 60 * 1000 if cutoff is not None else None
        timeline: list[tuple[int, ChatMessage]] = []

        for raw in messages:
            timestamp = self._coerce_timestamp(raw.get("create_time"))
            if timestamp is None:
                continue
            if cutoff is not None and timestamp >= cutoff:
                continue
            if window_start is not None and timestamp < window_start:
                continue
            role = self._infer_role(raw.get("sender"))
            content = self._extract_message_text(raw)
            if not content:
                continue
            timeline.append((timestamp, ChatMessage(role=role, content=content)))

        if not timeline:
            return []

        timeline.sort(key=lambda item: item[0])
        selected: list[ChatMessage] = []
        last_timestamp: int | None = None
        max_gap = gap_minutes * 60 * 1000

        for timestamp, message in timeline:
            if last_timestamp is not None and timestamp - last_timestamp > max_gap:
                selected = []
            selected.append(message)
            last_timestamp = timestamp

        return selected

    def _extract_message_text(self, raw: dict[str, Any]) -> str:
        body = raw.get("body")
        content: str | None = None
        if isinstance(body, dict):
            raw_content = body.get("content")
            if isinstance(raw_content, str):
                content = raw_content
        if content is None:
            raw_content = raw.get("content")
            if isinstance(raw_content, str):
                content = raw_content
        if not content:
            return ""

        text = content
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            parsed_text = parsed.get("text")
            if isinstance(parsed_text, str):
                text = parsed_text
        text = self._strip_message_mentions(_MENTION_TAG_RE.sub("", text), raw)
        return " ".join(text.split()).strip()

    def _strip_message_mentions(self, text: str, raw: dict[str, Any]) -> str:
        mentions = raw.get("mentions")
        if not isinstance(mentions, list):
            return text
        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            key = mention.get("key")
            if isinstance(key, str) and key:
                text = text.replace(key, "")
        return text

    def _infer_role(self, sender: Any) -> str:
        sender_type = None
        if isinstance(sender, dict):
            sender_type = sender.get("sender_type")
        if sender_type in {"bot", "app", "application"}:
            return "eko"
        return "user"

    def _extract_sender_profile(self, sender: Any) -> dict[str, Any]:
        if not isinstance(sender, dict):
            return {}
        sender_id = sender.get("sender_id")
        if not isinstance(sender_id, dict):
            sender_id = {}
        profile: dict[str, Any] = {}
        open_id = sender_id.get("open_id") or sender.get("open_id") or sender.get("id")
        union_id = sender_id.get("union_id") or sender.get("union_id")
        if isinstance(open_id, str) and open_id:
            profile["sender_open_id"] = open_id
        if isinstance(union_id, str) and union_id:
            profile["sender_union_id"] = union_id
        return profile

    def _coerce_timestamp(self, raw_timestamp: Any) -> int | None:
        if isinstance(raw_timestamp, int):
            return raw_timestamp
        if isinstance(raw_timestamp, str):
            try:
                return int(raw_timestamp)
            except ValueError:
                return None
        return None

    async def _publish_status(self, session_id: str, payload: dict[str, Any]) -> None:
        redis_client = self._redis or redis_module.redis_client
        if redis_client is not None:
            await redis_client.publish(
                f"eko:feishu:publish:{session_id}",
                json.dumps(payload),
            )
