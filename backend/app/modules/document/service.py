"""
Document Service - 文档生成核心业务逻辑
"""
import json
import logging
from typing import AsyncIterator, Any

from app.config import settings
from app.core import redis_client as redis_module
from app.core.llm_client import LLMClient
from app.modules.document.schemas import (
    DocumentType,
    DocumentGenerationRequest,
    ChatMessage,
    KnowledgeDoc,
    BitableRecord,
)
from app.modules.feishu.service import FeishuService

logger = logging.getLogger(__name__)


class DocumentService:
    """文档服务"""

    def __init__(
        self,
        llm_client: LLMClient,
        feishu_service: FeishuService,
        redis_client: Any | None = None,
    ) -> None:
        self._llm = llm_client
        self._feishu = feishu_service
        self._redis = redis_client

    def _get_system_prompt(self, tone: str = "formal") -> str:
        """使用用户提供的专业 System Prompt"""
        style_desc = {
            "formal": "formal - 正式商务风格（默认）",
            "casual": "casual - 轻松随意风格",
            "friendly": "casual - 轻松随意风格",
            "technical": "technical - 技术文档风格",
        }

        return f"""你是 Eko 智能办公助手的文档生成模块。

Eko 的唤醒方式：在飞书群中 @Eko + 一句指令

你的任务是根据用户需求，结合三类信息（均来自飞书 API），生成结构清晰、内容详实的 Markdown 格式文稿。

## 三类信息来源（均可为空白）

创作时你将收到三类信息（均可为空白，不影响流程继续）：

1. **飞书群聊上下文**（通过飞书 API 获取）- 刚才讨论了什么，有什么共识和待办，可为空白
2. **飞书多维表格数据**（通过飞书 API 获取）- 项目数据、活动记录等结构化信息，可为空白
3. **RAG 知识库资料**（通过飞书文档 API 获取）- 过往的文档、模板、经验资料，可为空白

## 写作原则

1. **结构化** - 合理使用标题层级（#、##、###）
2. **逻辑性** - 内容有条理，前后连贯
3. **详实性** - 有具体内容，不空洞
4. **三源融合** - 自然结合实时聊天、表格数据、过往资料（如有）
5. **可流式** - 可以分章节输出，每章节相对独立

## 输出格式

严格使用 Markdown 格式，包含：
- 标题层级
- 有序/无序列表
- 段落
- 加粗/斜体（如需要）
- 分隔线（如需要）
- 表格（如需展示数据）

## 引用说明

当用到某类信息时，可以这样表示（可选）：
- "根据刚才的讨论..."（来自飞书聊天）
- "根据项目记录..."（来自 Bitable）
- "根据知识库资料..."（来自 RAG）

如果某类信息为空白，则无需引用。

## 风格选项

{style_desc.get(tone, "formal - 正式商务风格（默认）")}
"""

    def _format_chat_history(self, chat_history: list[ChatMessage]) -> str:
        """格式化聊天记录"""
        if not chat_history:
            return ""
        lines = ["## 飞书群聊上下文"]
        for msg in chat_history:
            lines.append(f"{msg.role}: {msg.content}")
        return "\n".join(lines)

    def _format_knowledge_docs(self, docs: list[KnowledgeDoc]) -> str:
        """格式化知识库文档"""
        if not docs:
            return ""
        lines = ["## RAG 知识库资料"]
        for doc in docs:
            lines.append(f"### {doc.title}")
            lines.append(f"{doc.content}")
            if doc.source:
                lines.append(f"*来源: {doc.source}*")
        return "\n".join(lines)

    def _format_bitable_records(self, records: list[BitableRecord]) -> str:
        """格式化多维表格数据"""
        if not records:
            return ""
        lines = ["## 飞书多维表格数据"]
        for record in records:
            if record.table_name:
                lines.append(f"### {record.table_name}")
            lines.append("```json")
            lines.append(json.dumps(record.fields, ensure_ascii=False, indent=2))
            lines.append("```")
        return "\n".join(lines)

    def _get_user_prompt(
        self,
        topic: str,
        requirement: str,
        chat_history: list[ChatMessage],
        knowledge_docs: list[KnowledgeDoc],
        bitable_records: list[BitableRecord],
    ) -> str:
        """构建用户提示词"""
        parts = []

        parts.append(f"## 用户需求")
        parts.append(f"**文档主题**: {topic}")
        parts.append(f"**具体需求**: {requirement}")

        # 添加上下文
        chat_str = self._format_chat_history(chat_history)
        if chat_str:
            parts.append("")
            parts.append(chat_str)

        knowledge_str = self._format_knowledge_docs(knowledge_docs)
        if knowledge_str:
            parts.append("")
            parts.append(knowledge_str)

        bitable_str = self._format_bitable_records(bitable_records)
        if bitable_str:
            parts.append("")
            parts.append(bitable_str)

        parts.append("")
        parts.append("---")
        parts.append("请根据以上信息开始生成文档：")

        return "\n".join(parts)

    async def generate_document(
        self,
        request: DocumentGenerationRequest,
    ) -> str:
        """生成完整文档（非流式）"""
        system_prompt = self._get_system_prompt(request.tone)
        user_prompt = self._get_user_prompt(
            request.topic,
            request.requirement,
            request.chat_history,
            request.knowledge_docs,
            request.bitable_records,
        )

        logger.info(f"Generating document for session: {request.session_id}")
        content = await self._llm.generate(system_prompt, user_prompt)
        logger.info(f"Document generated for session: {request.session_id}")

        return content

    async def generate_document_stream(
        self,
        request: DocumentGenerationRequest,
    ) -> AsyncIterator[str]:
        """流式生成文档"""
        system_prompt = self._get_system_prompt(request.tone)
        user_prompt = self._get_user_prompt(
            request.topic,
            request.requirement,
            request.chat_history,
            request.knowledge_docs,
            request.bitable_records,
        )

        logger.info(f"Streaming document for session: {request.session_id}")

        async for chunk in self._llm.generate_stream(system_prompt, user_prompt):
            yield chunk

    async def save_and_sync_document(
        self,
        session_id: str,
        title: str,
        content: str,
        app_token: str | None = None,
        table_id: str | None = None,
    ) -> dict[str, Any]:
        """保存文档并同步到飞书"""
        app_token = app_token or settings.FEISHU_BITABLE_APP_TOKEN or None
        table_id = table_id or settings.FEISHU_BITABLE_TABLE_ID or None

        try:
            result = await self._feishu.publish_markdown_to_feishu(
                title=title,
                markdown_content=content,
                app_token=app_token,
                table_id=table_id,
            )
            payload = {
                "session_id": session_id,
                "status": "completed",
                "document_url": result["document_url"],
                "record_id": result["record_id"],
            }
            await self._publish_status(session_id, payload)
            return payload
        except Exception as exc:
            logger.exception("Document sync failed for session %s", session_id)
            payload = {
                "session_id": session_id,
                "status": "failed",
                "document_url": None,
                "record_id": None,
                "error": str(exc),
            }
            await self._publish_status(session_id, payload)
            return payload

    async def _publish_status(self, session_id: str, payload: dict[str, Any]) -> None:
        redis_client = self._redis or redis_module.redis_client
        if redis_client is not None:
            await redis_client.publish(
                f"eko:document:sync:{session_id}",
                json.dumps(payload),
            )
