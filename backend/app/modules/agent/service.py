"""
Agent Service - Agent 核心业务逻辑，Subagent 架构
"""
import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

from app.config import settings
from app.core.llm_client import LLMClient
from app.core.redis_client import redis_client
from app.modules.agent.schemas import (
    AgentChatArtifact,
    AgentChatRequest,
    AgentChatResponse,
    AgentContext,
    AgentIntent,
    AgentRequest,
    AgentResponse,
    AgentStatus,
    BitableRecord,
    ChatMessage,
    KnowledgeDoc,
    SubagentType,
    SyncDocumentRequest,
    SyncDocumentResponse,
)
from app.modules.canvas.schemas import CanvasBoardTaskCreateRequest
from app.modules.canvas.service import CanvasService
from app.modules.document.schemas import DocumentGenerationRequest
from app.modules.document.service import DocumentService
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.service import FeishuService
from app.modules.ppt.schemas import PptDeckCreateRequest, PptPreferencesSchema
from app.modules.ppt.service import PptService

logger = logging.getLogger(__name__)


class RouterAgent:
    """路由 Agent - 意图识别"""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def classify_intent(self, instruction: str) -> AgentIntent:
        """识别用户意图"""
        system_prompt = """你是 Eko 的路由识别器。根据用户的指令，判断用户想要做什么。

返回值只能是以下三种之一：
- chat - 用户只是想闲聊或问问题
- document - 用户想生成文档、方案、报告、纪要等
- presentation - 用户想生成 PPT、演示文稿、展示材料

不要返回任何其他内容，只返回这三个单词之一。"""

        user_prompt = f"用户指令：{instruction}\n\n请判断意图："

        try:
            result = await self._llm.generate(system_prompt, user_prompt)
            result = result.strip().lower()

            if "document" in result:
                return AgentIntent.DOCUMENT
            elif "presentation" in result or "ppt" in result:
                return AgentIntent.PRESENTATION
            elif "chat" in result:
                return AgentIntent.CHAT

            # 启发式规则
            if any(keyword in instruction for keyword in ["写", "文档", "方案", "报告", "纪要", "总结"]):
                return AgentIntent.DOCUMENT
            if any(keyword in instruction for keyword in ["PPT", "演示", "幻灯片", "展示"]):
                return AgentIntent.PRESENTATION

            return AgentIntent.CHAT
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, fallback to chat")
            return AgentIntent.CHAT

    async def classify_chat_intent(self, message: str) -> AgentIntent:
        """识别 Agent chat 路由意图"""
        system_prompt = """You are Eko's intent router for agent chat requests.

Classify the user's message into exactly one of these intents:
- chat
- docx
- ppt
- board

Return only the intent label."""

        user_prompt = f"User message: {message}\n\nIntent:"

        try:
            result = (await self._llm.generate(system_prompt, user_prompt, temperature=0.0)).strip().lower()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Agent chat intent classification failed: %s", exc)
            result = ""

        if "board" in result:
            return AgentIntent.BOARD
        if result == "docx" or "docx" in result:
            return AgentIntent.DOCX
        if result == "ppt" or "presentation" in result:
            return AgentIntent.PPT
        if result == "chat":
            return AgentIntent.CHAT

        lowered = message.lower()
        if any(keyword in message for keyword in ["画板", "白板", "流程图", "架构图", "架构"]) or "board" in lowered:
            return AgentIntent.BOARD
        if any(keyword in message for keyword in ["ppt", "PPT", "演示", "幻灯片", "汇报"]):
            return AgentIntent.PPT
        if any(keyword in message for keyword in ["文档", "方案", "报告", "纪要", "总结", "写一份"]):
            return AgentIntent.DOCX
        return AgentIntent.CHAT


class CollectorSubagent:
    """资料收集 Subagent - 获取三类上下文"""

    def __init__(self, feishu_client: FeishuClient) -> None:
        self._feishu = feishu_client

    async def collect_context(
        self,
        user_context: Optional[AgentContext] = None,
    ) -> AgentContext:
        """收集上下文信息"""
        context = user_context or AgentContext()

        # TODO: 实际调用飞书 API 获取聊天记录、多维表格数据、RAG 资料
        # 这里先返回用户提供的上下文，或者空上下文
        logger.info("CollectorSubagent: 上下文收集完成")

        return context


class WriterSubagent:
    """写作 Subagent - 生成文档"""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def _get_system_prompt(self, style: str = "formal") -> str:
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

{style_desc.get(style, "formal - 正式商务风格（默认）")}
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
        instruction: str,
        context: AgentContext,
    ) -> str:
        """构建用户提示词"""
        parts = []

        parts.append(f"## 用户需求")
        parts.append(f"**用户指令**: {instruction}")

        # 添加上下文
        chat_str = self._format_chat_history(context.chat_history)
        if chat_str:
            parts.append("")
            parts.append(chat_str)

        knowledge_str = self._format_knowledge_docs(context.knowledge_docs)
        if knowledge_str:
            parts.append("")
            parts.append(knowledge_str)

        bitable_str = self._format_bitable_records(context.bitable_records)
        if bitable_str:
            parts.append("")
            parts.append(bitable_str)

        parts.append("")
        parts.append("---")
        parts.append("请根据以上信息开始生成文档：")

        return "\n".join(parts)

    async def generate(
        self,
        instruction: str,
        context: AgentContext,
        style: str = "formal",
    ) -> str:
        """生成文档（非流式）"""
        system_prompt = self._get_system_prompt(style)
        user_prompt = self._get_user_prompt(instruction, context)

        logger.info("WriterSubagent: 开始生成文档")
        content = await self._llm.generate(system_prompt, user_prompt)
        logger.info("WriterSubagent: 文档生成完成")

        return content

    async def generate_stream(
        self,
        instruction: str,
        context: AgentContext,
        style: str = "formal",
    ) -> AsyncIterator[str]:
        """生成文档（流式）"""
        system_prompt = self._get_system_prompt(style)
        user_prompt = self._get_user_prompt(instruction, context)

        logger.info("WriterSubagent: 开始流式生成文档")

        async for chunk in self._llm.generate_stream(system_prompt, user_prompt):
            yield chunk


class SyncSubagent:
    """同步 Subagent - 同步到飞书"""

    def __init__(self, feishu_service: FeishuService) -> None:
        self._feishu = feishu_service

    async def sync_to_feishu(
        self,
        title: str,
        content: str,
        app_token: Optional[str] = None,
        table_id: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """同步文档到飞书，返回 (document_url, record_id)"""
        # 使用默认配置（如果未提供）
        app_token = app_token or settings.FEISHU_BITABLE_APP_TOKEN or None
        table_id = table_id or settings.FEISHU_BITABLE_TABLE_ID or None

        logger.info("SyncSubagent: 开始同步到飞书")
        result = await self._feishu.publish_markdown_to_feishu(
            title=title,
            markdown_content=content,
            app_token=app_token,
            table_id=table_id,
        )
        return result["document_url"], result["record_id"]


class AgentService:
    """Agent 协调器 - 管理各 Subagent"""

    def __init__(
        self,
        llm_client: LLMClient,
        feishu_service: FeishuService,
        document_service: DocumentService,
        ppt_service: PptService,
        canvas_service: CanvasService,
    ) -> None:
        self._router = RouterAgent(llm_client)
        self._collector = CollectorSubagent(feishu_service._client)
        self._writer = WriterSubagent(llm_client)
        self._sync = SyncSubagent(feishu_service)
        self._llm = llm_client
        self._feishu = feishu_service
        self._document_service = document_service
        self._ppt_service = ppt_service
        self._canvas_service = canvas_service

    async def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        """Handle direct agent chat requests with intent-based routing."""
        intent = AgentIntent.CHAT
        try:
            intent = await self._router.classify_chat_intent(request.message)

            if intent == AgentIntent.DOCX:
                content = await self._document_service.generate_document(
                    DocumentGenerationRequest(
                        session_id=request.session_id,
                        topic=request.message,
                        requirement=request.message,
                    )
                )
                return AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.DOCX.value,
                    status="completed",
                    message="文档生成完成。",
                    artifact=AgentChatArtifact(
                        kind="docx",
                        content=content,
                    ),
                )

            if intent == AgentIntent.PPT:
                deck = self._ppt_service.create_deck(
                    PptDeckCreateRequest(
                        type="chat",
                        content=request.message,
                        preferences=PptPreferencesSchema(),
                    )
                )
                return AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.PPT.value,
                    status="completed",
                    message="PPT 已生成。",
                    artifact=AgentChatArtifact(
                        kind="ppt",
                        deck_id=deck.deck_id,
                    ),
                )

            if intent == AgentIntent.BOARD:
                if not request.sharing_url:
                    return AgentChatResponse(
                        session_id=request.session_id,
                        intent=AgentIntent.BOARD.value,
                        status="failed",
                        message="生成飞书画板需要 sharing_url。",
                        artifact=None,
                        error="missing sharing_url",
                    )

                board_task = self._canvas_service.create_board_task(
                    CanvasBoardTaskCreateRequest(
                        message=request.message,
                        sharing_url=request.sharing_url,
                    )
                )
                completed_task = self._canvas_service.run_board_task(board_task.task_id)
                is_failed = completed_task.status == "failed"
                return AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.BOARD.value,
                    status="failed" if is_failed else "completed",
                    message=completed_task.error_message if is_failed else "飞书画板任务已完成。",
                    artifact=AgentChatArtifact(
                        kind="board",
                        task_id=completed_task.task_id,
                        status=completed_task.status,
                        whiteboard_id=completed_task.whiteboard_id,
                        sharing_url=completed_task.sharing_url,
                        result_summary=completed_task.result_summary,
                        error_message=completed_task.error_message,
                    ),
                    error=completed_task.error_message if is_failed else None,
                )

            reply = await self._llm.generate(
                "你是 Eko 智能办公助手。请直接、友好地回答用户问题。",
                request.message,
            )
            return AgentChatResponse(
                session_id=request.session_id,
                intent=AgentIntent.CHAT.value,
                status="completed",
                message=reply,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent chat failed session=%s, error=%s", request.session_id, exc)
            response_intent = intent if intent in {
                AgentIntent.CHAT,
                AgentIntent.DOCX,
                AgentIntent.PPT,
                AgentIntent.BOARD,
            } else AgentIntent.CHAT
            return AgentChatResponse(
                session_id=request.session_id,
                intent=response_intent.value,
                status="failed",
                message="处理失败，请稍后重试",
                error=str(exc),
            )

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """处理用户请求（完整流程）"""
        session_id = request.session_id

        try:
            # 1. Router Agent - 意图识别
            logger.info(f"Agent: 开始路由 session={session_id}")
            intent = await self._router.classify_intent(request.instruction)
            logger.info(f"Agent: 识别到意图={intent}")

            if intent == AgentIntent.CHAT:
                return AgentResponse(
                    session_id=session_id,
                    status=AgentStatus.COMPLETED,
                    intent=intent,
                    message="你好！我可以帮你生成文档或演示文稿。请告诉我你想写什么？",
                )

            if intent == AgentIntent.PRESENTATION:
                return AgentResponse(
                    session_id=session_id,
                    status=AgentStatus.COMPLETED,
                    intent=intent,
                    message="PPT 生成功能即将上线，敬请期待！",
                )

            # 2. Collector Subagent - 资料收集
            logger.info(f"Agent: 开始收集资料 session={session_id}")
            context = await self._collector.collect_context(request.context)

            # 3. Writer Subagent - 生成文档
            logger.info(f"Agent: 开始写作 session={session_id}")
            content = await self._writer.generate(
                request.instruction,
                context,
                request.style,
            )

            return AgentResponse(
                session_id=session_id,
                status=AgentStatus.COMPLETED,
                intent=intent,
                message="文档生成完成！",
                content=content,
            )

        except Exception as e:
            logger.error(f"Agent: 处理失败 session={session_id}, error={e}")
            return AgentResponse(
                session_id=session_id,
                status=AgentStatus.FAILED,
                intent=AgentIntent.UNKNOWN,
                message="处理失败，请稍后重试",
                error=str(e),
            )

    async def process_stream(self, request: AgentRequest) -> AsyncIterator[AgentResponse]:
        """流式处理用户请求"""
        session_id = request.session_id

        # 1. Router Agent - 意图识别
        yield AgentResponse(
            session_id=session_id,
            status=AgentStatus.ROUTING,
            intent=AgentIntent.UNKNOWN,
            message="正在理解你的需求...",
        )

        intent = await self._router.classify_intent(request.instruction)

        if intent == AgentIntent.CHAT:
            yield AgentResponse(
                session_id=session_id,
                status=AgentStatus.COMPLETED,
                intent=intent,
                message="你好！我可以帮你生成文档或演示文稿。请告诉我你想写什么？",
            )
            return

        if intent == AgentIntent.PRESENTATION:
            yield AgentResponse(
                session_id=session_id,
                status=AgentStatus.COMPLETED,
                intent=intent,
                message="PPT 生成功能即将上线，敬请期待！",
            )
            return

        # 2. Collector Subagent - 资料收集
        yield AgentResponse(
            session_id=session_id,
            status=AgentStatus.COLLECTING,
            intent=intent,
            message="正在收集相关资料...",
        )

        context = await self._collector.collect_context(request.context)

        # 3. Writer Subagent - 流式生成
        yield AgentResponse(
            session_id=session_id,
            status=AgentStatus.WRITING,
            intent=intent,
            message="正在生成文档...",
        )

        full_content = ""
        async for chunk in self._writer.generate_stream(
            request.instruction,
            context,
            request.style,
        ):
            full_content += chunk
            yield AgentResponse(
                session_id=session_id,
                status=AgentStatus.WRITING,
                intent=intent,
                message="正在生成文档...",
                content=full_content,
            )

        # 4. 完成
        yield AgentResponse(
            session_id=session_id,
            status=AgentStatus.COMPLETED,
            intent=intent,
            message="文档生成完成！",
            content=full_content,
        )

    async def sync_document(self, request: SyncDocumentRequest) -> SyncDocumentResponse:
        """同步文档到飞书"""
        session_id = request.session_id

        try:
            # 先通知开始
            if redis_client:
                await redis_client.publish(
                    f"eko:agent:sync:{session_id}",
                    json.dumps({"status": "syncing"}),
                )

            # Sync Subagent - 同步飞书
            logger.info(f"Agent: 开始同步 session={session_id}")
            document_url, record_id = await self._sync.sync_to_feishu(
                request.title,
                request.content,
                request.app_token,
                request.table_id,
            )

            # 发布完成消息
            if redis_client:
                await redis_client.publish(
                    f"eko:agent:sync:{session_id}",
                    json.dumps({
                        "status": "completed",
                        "document_url": document_url,
                        "record_id": record_id,
                    }),
                )

            return SyncDocumentResponse(
                session_id=session_id,
                status=AgentStatus.COMPLETED,
                document_url=document_url,
                record_id=record_id,
                message="文档已就绪，已为您归档至多维表格",
            )

        except Exception as e:
            logger.error(f"Agent: 同步失败 session={session_id}, error={e}")

            if redis_client:
                await redis_client.publish(
                    f"eko:agent:sync:{session_id}",
                    json.dumps({"status": "failed", "error": str(e)}),
                )

            return SyncDocumentResponse(
                session_id=session_id,
                status=AgentStatus.FAILED,
                message="同步失败，请稍后重试",
                error=str(e),
            )

    def create_task(self) -> Any:
        from app.modules.agent.schemas import AgentTaskSchema
        return AgentTaskSchema(task_id="stub-task")
