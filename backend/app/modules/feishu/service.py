from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.config import settings
from app.core import redis_client as redis_module
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.schemas import FeishuCardSchema

logger = logging.getLogger(__name__)


class FeishuService:
    def __init__(self, client: FeishuClient, redis_client: Any | None = None) -> None:
        self._client = client
        self._redis = redis_client

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return self._client.get_card(card_id)

    async def create_import_ticket(
        self,
        markdown_content: str,
        title: str,
    ) -> str:
        return await asyncio.to_thread(
            self._client.create_import_task,
            markdown_content,
            title,
        )

    async def complete_import_task(
        self,
        ticket: str,
        title: str,
        app_token: str | None = None,
        table_id: str | None = None,
    ) -> dict[str, Any]:
        """等待导入完成并可选写入多维表格"""
        document_url = None
        max_attempts = 30  # 最多等待30秒
        for attempt in range(max_attempts):
            result = await asyncio.to_thread(
                self._client.get_import_task_result,
                ticket,
            )
            if result is not None:
                document_url = result["url"]
                break
            await asyncio.sleep(1)

        if document_url is None:
            raise Exception("Import task timeout after 30 seconds")

        logger.info(f"Import completed: url={document_url}")

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
                logger.info(f"Created bitable record: record_id={record_id}")
            except Exception as exc:
                logger.warning(f"Create bitable record skipped: {exc}")

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
        """将 Markdown 文档发布为飞书文档并同步到多维表格

        Args:
            title: 文档标题
            markdown_content: Markdown 内容
            app_token: 多维表格应用 token（可选）
            table_id: 多维表格数据表 ID（可选）

        Returns:
            包含 document_url 和 record_id 的结果
        """
        # 1. 创建导入任务
        ticket = ticket or await self.create_import_ticket(markdown_content, title)
        logger.info(f"Created import task: ticket={ticket}")
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
        """后台异步发布任务，完成后通过 Redis Pub/Sub 通知前端"""
        try:
            result = await self.publish_markdown_to_feishu(
                title, markdown_content, app_token, table_id, ticket
            )
            # 通过 Redis Pub/Sub 发布完成事件
            message = {
                "session_id": session_id,
                "status": "completed",
                "document_url": result["document_url"],
                "record_id": result["record_id"],
            }
            await self._publish_status(session_id, message)
            logger.info(f"Publish completed for session {session_id}")
        except Exception as e:
            logger.error(f"Publish failed for session {session_id}: {e}")
            message = {
                "session_id": session_id,
                "status": "failed",
                "error": str(e),
            }
            await self._publish_status(session_id, message)

    def get_import_status(self, ticket: str) -> dict[str, Any] | None:
        """查询导入任务状态"""
        return self._client.get_import_task_status(ticket)

    async def _publish_status(self, session_id: str, payload: dict[str, Any]) -> None:
        redis_client = self._redis or redis_module.redis_client
        if redis_client is not None:
            await redis_client.publish(
                f"eko:feishu:publish:{session_id}",
                json.dumps(payload),
            )
