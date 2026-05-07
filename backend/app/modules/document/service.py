"""
Document Service - 文档生成核心业务逻辑
"""
import json
import logging
import re
from typing import AsyncIterator, Any
from urllib.parse import urlparse

from app.config import settings
from app.core import redis_client as redis_module
from app.core.llm_client import LLMClient
from app.modules.document.schemas import (
    DocumentType,
    DocumentAutoSyncRequest,
    DocumentEditRequest,
    DocumentGenerationRequest,
    ChatMessage,
    KnowledgeDoc,
    BitableRecord,
)
from app.modules.feishu.service import FeishuService
from app.modules.sync.service import SyncService

logger = logging.getLogger(__name__)

_SUMMARY_HEADING_RE = re.compile(
    r"(?ms)^#{1,6}\s*(?:总结|总\s*结|结论|小结|Summary|Conclusion)\s*.*?(?=^#{1,6}\s+\S|\Z)"
)

_RAG_FACT_KEYWORDS = (
    "总部",
    "研发",
    "星途",
    "星枢",
    "B端",
    "C端",
    "MaaS",
    "业务布局",
    "安全备案",
    "商业模式",
    "营收",
    "收入",
    "三大板块",
    "云端调用",
    "政企",
    "定制化",
    "模型授权",
    "长期运维",
    "增值服务",
    "战略合作",
    "生态渠道",
    "渠道联营",
    "渠道合作",
    "行业解决方案",
    "算力硬件",
    "合作伙伴",
)

_GENERIC_PLACEHOLDER_PATTERNS = (
    "[请",
    "请在此处填写",
    "请填写",
    "待补充",
    "待填写",
    "TODO",
    "TBD",
)

_GENERIC_OFFICE_TEMPLATE_TERMS = (
    "智能办公平台",
    "即时通讯",
    "智能日历",
    "审批流自动化",
    "项目任务管理",
    "RPA（机器人流程自动化）",
    "应用市场",
)


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

    def _contains_unfilled_template(self, content: str) -> bool:
        return any(pattern in content for pattern in ("[请填写", "[具体", "[负责人", "[日期", "[某部门", "请填写具体"))

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

    def _format_knowledge_fact_anchors(self, docs: list[KnowledgeDoc]) -> str:
        anchors = self._knowledge_fact_anchor_sentences(docs)
        if not anchors:
            return ""
        return "## RAG 原文关键事实（生成时必须逐字包含，且不得改写事实）\n" + "\n".join(
            f"- {anchor}" for anchor in anchors
        )

    def _knowledge_fact_anchor_sentences(self, docs: list[KnowledgeDoc]) -> list[str]:
        if not docs:
            return []
        anchors: list[str] = []
        for doc in docs:
            sentences = re.split(r"(?<=[。！？\n])", doc.content)
            for sentence in sentences:
                normalized = sentence.strip()
                if normalized and any(keyword in normalized for keyword in _RAG_FACT_KEYWORDS):
                    anchors.append(normalized)
                if len(anchors) >= 12:
                    break
            if len(anchors) >= 12:
                break
        return anchors

    def _contains_generic_placeholder(self, content: str) -> bool:
        return any(pattern in content for pattern in _GENERIC_PLACEHOLDER_PATTERNS)

    def _contains_generic_office_template(self, content: str, docs: list[KnowledgeDoc]) -> bool:
        if not docs:
            return False
        corpus = self._knowledge_corpus(docs)
        template_hits = [term for term in _GENERIC_OFFICE_TEMPLATE_TERMS if term in content and term not in corpus]
        if len(template_hits) < 3:
            return False
        source_identity_hits = [
            term
            for term in ("星途", "星枢", "大模型", "云端调用", "模型授权", "政企")
            if term in corpus and term in content
        ]
        return not source_identity_hits

    def _knowledge_corpus(self, docs: list[KnowledgeDoc]) -> str:
        return "\n".join(doc.content for doc in docs)

    def _ungrounded_location_terms(self, content: str, docs: list[KnowledgeDoc]) -> list[str]:
        if not docs:
            return []
        corpus = self._knowledge_corpus(docs)
        location_terms = (
            "北京",
            "北京海淀",
            "上海",
            "深圳",
            "杭州",
            "广州",
            "南京",
            "成都",
            "武汉",
            "西安",
            "硅谷",
        )
        return [
            term
            for term in location_terms
            if term in content and term not in corpus
        ]

    def _requires_grounded_fallback(self, content: str, docs: list[KnowledgeDoc]) -> bool:
        if not docs:
            return False
        if self._contains_generic_placeholder(content):
            return True
        if self._contains_generic_office_template(content, docs):
            return True
        anchors = self._knowledge_fact_anchor_sentences(docs)
        missing_anchor = any(anchor not in content for anchor in anchors[:4])
        return missing_anchor or bool(self._ungrounded_location_terms(content, docs))

    def _build_grounded_fallback_document(
        self,
        topic: str,
        requirement: str,
        docs: list[KnowledgeDoc],
    ) -> str:
        title = topic.strip() or "基于知识库的文档"
        anchors = self._knowledge_fact_anchor_sentences(docs)
        if not anchors:
            anchors = [
                sentence.strip()
                for doc in docs
                for sentence in re.split(r"(?<=[。！？\n])", doc.content)
                if sentence.strip()
            ][:8]

        source_title = docs[0].title if docs else "RAG 知识库资料"
        lines = [
            f"# {title}",
            "",
            f"本文依据知识库资料《{source_title}》生成；涉及事实信息时，以下内容直接采用知识库原文，不新增知识库未提供的信息。",
            "",
            "## 用户需求",
            requirement.strip() or "生成文档",
            "",
            "## 知识库原文关键事实",
        ]
        lines.extend(f"- {anchor}" for anchor in anchors)
        lines.extend(
            [
                "",
                "## 公司介绍正文",
            ]
        )
        lines.extend(anchors)
        return "\n\n".join(lines).strip() + "\n"

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
            parts.append("")
            parts.append("## RAG 事实约束")
            parts.append("以上 RAG 知识库资料是本次生成的事实依据。涉及公司名称、总部地点、研发中心、产品名称、业务布局、行业领域、资质备案等事实时，必须严格以 RAG 原文为准，关键事实句必须逐字写入正文。")
            parts.append("不得新增、替换或编造 RAG 中没有出现的地点、机构、产品、业务、数据或资质；如果用户要求的细节在 RAG 中不存在，请明确写“知识库未提供”。")
            fact_anchors = self._format_knowledge_fact_anchors(knowledge_docs)
            if fact_anchors:
                parts.append("")
                parts.append(fact_anchors)

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
        content = self.ground_document_if_needed(request, content)
        logger.info(f"Document generated for session: {request.session_id}")

        return content

    def ground_document_if_needed(self, request: DocumentGenerationRequest, content: str) -> str:
        if not self._requires_grounded_fallback(content, request.knowledge_docs):
            return content
        logger.warning(
            "Document generation failed RAG grounding check; using source-grounded fallback. session=%s",
            request.session_id,
        )
        return self._build_grounded_fallback_document(
            request.topic,
            request.requirement,
            request.knowledge_docs,
        )

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

    async def edit_document(self, request: DocumentEditRequest) -> str:
        """Edit an existing Markdown document according to a user instruction."""
        deterministic = self._try_deterministic_edit(request.current_content, request.instruction)
        if deterministic is not None:
            return deterministic

        system_prompt = """你是 Eko 智能办公助手的文档编辑模块。

你只负责修改用户提供的现有 Markdown 文档，不要重新生成一份全新文档。

要求：
1. 严格保留与用户修改要求无关的内容。
2. 按用户要求删除、改写、补充或调整对应部分。
3. 输出完整修改后的 Markdown 正文。
4. 不要解释修改过程，不要输出 JSON。"""
        user_prompt = "\n".join(
            [
                "## 用户编辑要求",
                request.instruction,
                "",
                "## 当前文档",
                request.current_content,
                "",
                "请输出修改后的完整 Markdown：",
            ]
        )
        logger.info("Editing document for session: %s", request.session_id)
        return await self._llm.generate(system_prompt, user_prompt)

    def _try_deterministic_edit(self, content: str, instruction: str) -> str | None:
        normalized = instruction.strip().lower()
        wants_delete = any(keyword in instruction for keyword in ["删除", "删掉", "去掉", "移除"]) or "remove" in normalized
        targets_summary = any(keyword in instruction for keyword in ["总结", "小结", "结论"]) or "summary" in normalized
        if not wants_delete or not targets_summary:
            return None

        edited = _SUMMARY_HEADING_RE.sub("", content).strip()
        if edited != content.strip():
            return f"{edited}\n"
        return None

    async def save_and_sync_document(
        self,
        session_id: str,
        title: str,
        content: str,
        app_token: str | None = None,
        table_id: str | None = None,
        sync_service: SyncService | None = None,
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
            if sync_service is not None:
                await sync_service.publish_task_completed(
                    session_id,
                    intent="docx",
                    message="文档已同步到飞书。",
                    status="completed",
                    artifact={
                        "kind": "docx",
                        "content": content,
                        "status": "completed",
                        "current_step": "文档已保存并同步",
                        "sharing_url": result["document_url"],
                        "result_summary": "文档已同步到飞书。",
                    },
                    messages=None,
                    error=None,
                )
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
            if sync_service is not None:
                await sync_service.publish_task_completed(
                    session_id,
                    intent="docx",
                    message="文档同步失败。",
                    status="failed",
                    artifact={
                        "kind": "docx",
                        "content": content,
                        "status": "failed",
                        "current_step": "文档同步失败",
                        "sharing_url": None,
                        "result_summary": "文档同步失败。",
                        "error_message": str(exc),
                    },
                    messages=None,
                    error=str(exc),
                )
            await self._publish_status(session_id, payload)
            return payload

    async def auto_sync_markdown_document(self, request: DocumentAutoSyncRequest) -> dict[str, Any]:
        """Publish the current editor content to Feishu without invoking the LLM."""
        try:
            result = await self._feishu.publish_markdown_to_feishu(
                title=request.title.strip() or "Eko 文档",
                markdown_content=request.content,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Document auto sync failed for session %s", request.session_id)
            return {
                "session_id": request.session_id,
                "status": "failed",
                "message": f"自动同步失败：{exc}",
                "document_url": request.current_url,
                "record_id": None,
                "error": str(exc),
            }

        document_url = result.get("document_url") if isinstance(result, dict) else None
        if not isinstance(document_url, str) or not document_url:
            document_url = request.current_url

        chat_id = self._extract_feishu_chat_id(request.session_id)
        if chat_id and document_url:
            document_id = self._extract_docx_token_from_url(document_url)
            if document_id:
                try:
                    await self._feishu.add_docx_permission_for_chat(document_id, chat_id, perm="edit")
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Grant auto-synced docx permission failed session=%s doc=%s chat=%s: %s",
                        request.session_id,
                        document_id,
                        chat_id,
                        exc,
                    )

        return {
            "session_id": request.session_id,
            "status": "completed",
            "message": "文档已自动同步到飞书。",
            "document_url": document_url,
            "record_id": result.get("record_id") if isinstance(result, dict) else None,
        }

    def _extract_feishu_chat_id(self, session_id: str) -> str | None:
        parts = session_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "feishu":
            return None
        return parts[1] or None

    def _extract_docx_token_from_url(self, document_url: str) -> str | None:
        parsed = urlparse(document_url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        if len(segments) >= 2 and segments[-2] == "docx":
            return segments[-1]
        return None

    async def _publish_status(self, session_id: str, payload: dict[str, Any]) -> None:
        redis_client = self._redis or redis_module.redis_client
        if redis_client is not None:
            await redis_client.publish(
                f"eko:document:sync:{session_id}",
                json.dumps(payload),
            )
