from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.config import settings
from app.core import redis_client as redis_module
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

    async def _publish_status(self, session_id: str, payload: dict[str, Any]) -> None:
        redis_client = self._redis or redis_module.redis_client
        if redis_client is not None:
            await redis_client.publish(
                f"eko:feishu:publish:{session_id}",
                json.dumps(payload),
            )
