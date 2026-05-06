"""
Agent Service - Agent 核心业务逻辑，Subagent 架构
"""
import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator, Optional
from urllib.parse import urlparse

from app.config import settings
from app.core.llm_client import LLMClient
from app.core.redis_client import redis_client
from app.modules.agent.schemas import (
    AgentChatArtifact,
    AgentChatRequest,
    AgentChatResponse,
    AgentContext,
    AgentIntent,
    AgentPlanFinalOutput,
    AgentPlanStep,
    AgentRequest,
    AgentResponse,
    AgentStatus,
    AgentTaskPlan,
    BitableRecord,
    ChatMessage,
    KnowledgeDoc,
    SubagentType,
    SyncDocumentRequest,
    SyncDocumentResponse,
)
from app.modules.agent.context import AgentContextAssembler
from app.modules.agent.planner import PlannerAgent
from app.modules.agent.events import AgentEventProtocol
from app.modules.agent.rag import AgentRAGRetriever
from app.modules.agent.runtime import AgentRuntime
from app.modules.agent.tools import AgentToolRegistry
from app.modules.canvas.schemas import CanvasBoardTaskCreateRequest, CanvasBoardTaskSchema
from app.modules.canvas.service import CanvasService
from app.modules.document.schemas import (
    BitableRecord as DocumentBitableRecord,
    DocumentEditRequest,
    DocumentGenerationRequest,
    KnowledgeDoc as DocumentKnowledgeDoc,
)
from app.modules.document.schemas import ChatMessage as DocumentChatMessage
from app.modules.document.service import DocumentService
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.service import FeishuService
from app.modules.aippt.schemas import PPTGenerationRequest
from app.modules.aippt.service import AIPPTService
from app.modules.sync.service import SyncService
from app.modules.rag.service import RagService

logger = logging.getLogger(__name__)

_NEW_DOCUMENT_KEYWORDS = (
    "新建",
    "重新生成",
    "重新写",
    "重写一份",
    "另写",
    "另起",
    "再写一份",
    "再生成一份",
    "生成新",
    "新文档",
    "new document",
    "create new",
    "regenerate",
)

_ARTIFACT_EDIT_KEYWORDS = (
    "改",
    "修改",
    "调整",
    "优化",
    "完善",
    "扩充",
    "丰富",
    "补充",
    "详细",
    "太少",
    "删除",
    "删去",
    "去掉",
    "移除",
    "替换",
    "精简",
    "缩短",
    "加上",
    "加入",
    "增加",
    "新增",
    "改成",
    "改为",
    "变成",
    "换",
    "换成",
    "替换为",
    "放大",
    "缩小",
    "重排",
    "移动",
    "字体",
    "颜色",
    "标题",
    "内容",
    "更正式",
    "更口语",
    "多一点",
    "少一点",
    "第一页",
    "第二页",
    "第三页",
    "第四页",
    "第五页",
    "第六页",
    "第一张",
    "第二张",
    "第三张",
    "第四张",
    "第五张",
    "第六张",
    "这一页",
    "这页",
    "这张",
    "当前",
    "继续",
)

_ARTIFACT_CREATE_KEYWORDS = (
    "新建",
    "重新生成",
    "重新做",
    "再生成一份",
    "再做一份",
    "另做",
    "另起",
    "生成一个新的",
    "生成一份新的",
    "新文档",
    "新ppt",
    "新PPT",
    "新画板",
)


class RouterAgent:
    """路由 Agent - 意图识别"""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client
        self._tool_registry = AgentToolRegistry()

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
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tool_registry.list_specs()
        ]
        system_prompt = """你是 Eko 在飞书群聊中的工具选择器。你必须根据用户真实要完成的办公动作，从可用工具中选择 primary_tool，而不是做关键词匹配。

选择原则：
1. 先理解用户想要的产物或动作，再选择最合适的工具。
2. 不要因为出现“生成”就默认 docx；“生成思路图/脑图/流程图/架构图/导图”应选择 board。
3. 如果用户要演示文稿、幻灯片、PPT、路演或汇报材料，选择 ppt。
4. 如果用户要报告、方案、文案、纪要、文章、介绍等文字文档，选择 docx。
5. 如果用户只是问问题，不需要创建办公产物，选择 chat。
6. 如果需要修改已有产物，优先选择对应 edit 工具。

只返回 JSON，不要 Markdown，不要解释。格式：
{"primary_tool":"chat|docx|docx_edit|ppt|ppt_create|ppt_edit|board|knowledge_search|artifact_lookup|sync","intent":"chat|docx|ppt|board","confidence":0.0到1.0,"reason":"不超过20字"}"""

        user_prompt = (
            f"用户消息：{message}\n\n"
            f"可用工具 JSON：{json.dumps(tools, ensure_ascii=False)}\n\n"
            "请选择 primary_tool，并输出 JSON："
        )

        try:
            result = (await self._llm.generate(system_prompt, user_prompt, temperature=0.0)).strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Agent chat intent classification failed: %s", exc)
            result = ""

        model_intent = self._parse_model_intent(result)
        if model_intent is not None:
            return model_intent

        deterministic_intent = self._deterministic_chat_intent(message)
        if deterministic_intent is not None:
            return deterministic_intent
        return AgentIntent.CHAT

    def _deterministic_chat_intent(self, message: str) -> AgentIntent | None:
        normalized = message.lower()
        if any(
            keyword in message
            for keyword in ["画板", "白板", "流程图", "架构图", "思维导图", "思路图", "脑图", "导图", "泳道图"]
        ) or "board" in normalized:
            return AgentIntent.BOARD
        if any(keyword in message for keyword in ["ppt", "PPT", "演示", "幻灯片", "路演", "汇报材料", "展示材料", "项目展示"]) or re.search(r"\bpresentation\b|\bslides?\b", normalized):
            return AgentIntent.PPT
        if (
            any(
                keyword in message
                for keyword in [
                    "文档",
                    "方案",
                    "报告",
                    "纪要",
                    "总结",
                    "草稿",
                    "文案",
                    "文字",
                    "说明",
                    "介绍",
                    "分析",
                    "提纲",
                    "大纲",
                    "写一份",
                    "写一段",
                    "生成一段",
                    "生成一篇",
                    "起草",
                    "整理成",
                    "输出",
                ]
            )
            or re.search(r"\bdocx?\b|\breport\b", normalized)
            or re.search(r"\d+\s*字", message)
        ):
            return AgentIntent.DOCX
        return None

    def _parse_model_intent(self, result: str) -> AgentIntent | None:
        normalized = result.strip().lower()
        if not normalized:
            return None

        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            parsed = None

        intent_value = ""
        tool_value = ""
        confidence = 1.0
        if isinstance(parsed, dict):
            raw_intent = parsed.get("intent")
            intent_value = raw_intent.strip().lower() if isinstance(raw_intent, str) else ""
            raw_tool = parsed.get("primary_tool") or parsed.get("tool")
            tool_value = raw_tool.strip().lower() if isinstance(raw_tool, str) else ""
            raw_confidence = parsed.get("confidence")
            if isinstance(raw_confidence, int | float):
                confidence = float(raw_confidence)
        else:
            intent_value = normalized

        if confidence < 0.45:
            return None
        tool_intent = self._intent_from_tool(tool_value)
        if tool_intent is not None:
            return tool_intent
        if intent_value == "board":
            return AgentIntent.BOARD
        if intent_value == "docx" or intent_value == "document":
            return AgentIntent.DOCX
        if intent_value == "ppt" or intent_value == "presentation":
            return AgentIntent.PPT
        if intent_value == "chat":
            return AgentIntent.CHAT
        return None

    def _intent_from_tool(self, tool_name: str) -> AgentIntent | None:
        if tool_name in {"docx", "docx_edit"}:
            return AgentIntent.DOCX
        if tool_name in {"ppt", "ppt_create", "ppt_edit"}:
            return AgentIntent.PPT
        if tool_name == "board":
            return AgentIntent.BOARD
        if tool_name in {"chat", "knowledge_search", "artifact_lookup"}:
            return AgentIntent.CHAT
        return None


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
        canvas_service: CanvasService,
        aippt_service: AIPPTService | None = None,
        sync_service: SyncService | None = None,
        rag_service: RagService | None = None,
    ) -> None:
        self._router = RouterAgent(llm_client)
        self._planner = PlannerAgent(llm_client)
        self._collector = CollectorSubagent(feishu_service._client)
        self._writer = WriterSubagent(llm_client)
        self._sync = SyncSubagent(feishu_service)
        self._llm = llm_client
        self._feishu = feishu_service
        self._document_service = document_service
        self._canvas_service = canvas_service
        self._aippt_service = aippt_service
        self._sync_service = sync_service
        self._rag_service = rag_service
        self._context_assembler = AgentContextAssembler()
        self._runtime = AgentRuntime(
            planner=self._planner,
            retriever=AgentRAGRetriever(rag_service=rag_service),
            tool_handlers={
                "docx": self._runtime_docx_tool,
                "ppt": self._runtime_ppt_tool,
                "board": self._runtime_board_tool,
            },
        )

    def _extract_ppt_page_count(self, message: str) -> int:
        match = re.search(r"(\d{1,2})\s*(?:页|p|P|slides?|张)", message)
        if not match:
            return 6
        return max(1, min(20, int(match.group(1))))

    def _build_sync_messages(
        self,
        request: AgentChatRequest,
        response: AgentChatResponse,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        user_message: dict[str, Any] = {
            "role": "user",
            "content": request.message,
        }
        if request.sender:
            user_message.update(request.sender)
        messages.append(user_message)

        assistant_message = response.message
        if response.error:
            assistant_message = f"{response.message}: {response.error}"
        messages.append(
            {
                "role": "assistant",
                "content": assistant_message,
            }
        )

        return messages

    async def _build_merged_sync_messages(
        self,
        request: AgentChatRequest,
        response: AgentChatResponse,
    ) -> list[dict[str, Any]]:
        existing: list[dict[str, Any]] = []
        if self._sync_service is not None and hasattr(self._sync_service, "get_session"):
            session = await self._sync_service.get_session(response.session_id)
            if session is not None and session.messages:
                existing = [dict(message) for message in session.messages]

        assistant_message = response.message
        if response.error:
            assistant_message = f"{response.message}: {response.error}"
        return self._merge_current_turn_messages(existing, request, assistant_message)

    def _merge_current_turn_messages(
        self,
        existing: list[dict[str, Any]],
        request: AgentChatRequest,
        assistant_message: str,
    ) -> list[dict[str, Any]]:
        current_user_message: dict[str, Any] = {
            "role": "user",
            "content": request.message,
        }
        if request.sender:
            current_user_message.update(request.sender)

        def role_of(message: dict[str, Any]) -> str:
            return str(message.get("role") or "").lower()

        def is_assistant(message: dict[str, Any]) -> bool:
            return role_of(message) in {"assistant", "eko", "bot", "system"}

        current_user_indexes = [
            index
            for index, message in enumerate(existing)
            if role_of(message) == "user" and str(message.get("content") or "") == request.message
        ]
        if current_user_indexes:
            turn_start = current_user_indexes[-1]
            for previous_index in reversed(current_user_indexes[:-1]):
                if all(is_assistant(message) for message in existing[previous_index + 1 : turn_start]):
                    turn_start = previous_index
                else:
                    break
            next_user_index = next(
                (
                    index
                    for index in range(turn_start + 1, len(existing))
                    if role_of(existing[index]) == "user" and str(existing[index].get("content") or "") != request.message
                ),
                len(existing),
            )
            normalized = existing[: turn_start + 1] + existing[next_user_index:]
        else:
            normalized = [*existing, current_user_message]

        if normalized and is_assistant(normalized[-1]) and str(normalized[-1].get("content") or "") == assistant_message:
            return normalized
        normalized.append({"role": "assistant", "content": assistant_message})
        return normalized

    async def _publish_chat_result(
        self,
        request: AgentChatRequest,
        response: AgentChatResponse,
    ) -> None:
        if self._sync_service is None:
            return

        if response.status == "completed":
            artifact = response.artifact.model_dump() if response.artifact is not None else None
            await self._sync_service.publish_task_completed(
                response.session_id,
                intent=response.intent,
                message=response.message,
                status=response.status,
                artifact=artifact,
                messages=await self._build_merged_sync_messages(request, response),
                error=response.error,
            )
            return

        await self._sync_service.publish_error(response.session_id, response.message, response.error)

    async def _create_plan_with_timeout(
        self,
        request: AgentChatRequest,
        intent: AgentIntent,
    ) -> AgentTaskPlan:
        try:
            return await asyncio.wait_for(
                self._planner.create_plan(
                    request.message,
                    routed_intent=intent,
                    context=request.context,
                ),
                timeout=6.0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Planner timed out or failed session=%s, fallback plan used: %s", request.session_id, exc)
            return self._planner._fallback_plan(request.message, intent)

    async def _prepare_agent_turn(
        self,
        request: AgentChatRequest,
        intent: AgentIntent,
        session_artifact: AgentChatArtifact | None,
        *,
        execute_tools: bool = False,
    ):
        return await self._runtime.prepare_turn(
            request,
            routed_intent=intent,
            current_artifact=session_artifact,
            execute_tools=execute_tools,
        )

    def _replace_plan_trace(self, trace_events: list[Any], plan: AgentTaskPlan | None) -> None:
        if plan is None:
            return
        for event in reversed(trace_events):
            if getattr(event, "type", None) == "plan_created":
                event.message = plan.visible_summary or plan.summary
                event.data = {"plan": plan.model_dump()}
                return

    def _runtime_tool_result(self, runtime_turn: Any, tool_name: str) -> dict[str, Any] | None:
        for item in getattr(runtime_turn, "tool_results", []):
            if item.get("tool") == tool_name and isinstance(item.get("result"), dict):
                return item["result"]
        return None

    def _events_from_traces(self, trace_events: list[Any]) -> list[Any]:
        return AgentEventProtocol.from_traces(trace_events)

    async def _runtime_docx_tool(
        self,
        instruction: str,
        session_id: str | None = None,
        retrieved_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        knowledge_docs = self._knowledge_docs_from_retrieved_context(retrieved_context)
        request = AgentChatRequest(
            session_id=session_id or "runtime",
            message=instruction,
            context=AgentContext(knowledge_docs=knowledge_docs) if knowledge_docs else None,
            planning_enabled=False,
        )
        content = await self._generate_document_with_realtime_stream(request)
        return {"content": content}

    async def _runtime_ppt_tool(
        self,
        instruction: str,
        session_id: str | None = None,
        design_mode: str | None = None,
        retrieved_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self._aippt_service is None:
            raise RuntimeError("aippt_service is not configured")
        request = AgentChatRequest(
            session_id=session_id or "runtime",
            message=instruction,
            planning_enabled=False,
        )
        resolved_design_mode = design_mode or "template"
        job = self._aippt_service.create_job_from_request(
            PPTGenerationRequest(
                topic=self._build_ppt_topic(request, session_artifact=None),
                page_count=self._resolve_ppt_page_count(request, session_artifact=None),
                style="clean_business",
                design_mode=resolved_design_mode,
            )
        )
        if hasattr(job, "model_dump"):
            return job.model_dump()
        return {
            "job_id": getattr(job, "job_id", None),
            "status": getattr(job, "status", None),
            "progress": getattr(job, "progress", None),
            "current_step": getattr(job, "current_step", None),
            "download_url": getattr(job, "download_url", None),
            "error": getattr(job, "error", None),
        }

    async def _runtime_board_tool(
        self,
        instruction: str,
        session_id: str | None = None,
        sharing_url: str | None = None,
        retrieved_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        knowledge_docs = self._knowledge_docs_from_retrieved_context(retrieved_context)
        grounded_instruction = self._append_knowledge_context_to_instruction(instruction, knowledge_docs)
        created_board_document: dict[str, str] | None = None
        if not sharing_url:
            created_board_document = await self._feishu.create_board_document(
                title=f"Eko 画板 - {instruction[:24]}",
            )
            sharing_url = created_board_document["sharing_url"]
        board_task = self._canvas_service.create_board_task(
            CanvasBoardTaskCreateRequest(
                message=grounded_instruction,
                sharing_url=sharing_url,
            )
        )
        completed_task = self._canvas_service.run_board_task(board_task.task_id)
        result = completed_task.model_dump() if hasattr(completed_task, "model_dump") else dict(completed_task)
        if created_board_document is not None:
            result["created_board_document"] = created_board_document
        return result

    def _knowledge_docs_from_retrieved_context(
        self,
        retrieved_context: list[dict[str, Any]] | None,
    ) -> list[KnowledgeDoc]:
        return [
            KnowledgeDoc(
                title=str(item.get("title") or "RAG 命中资料"),
                content=str(item.get("content") or ""),
                source=str(item.get("source_id") or item.get("source") or ""),
            )
            for item in (retrieved_context or [])
            if str(item.get("source_type") or "") == "knowledge_doc" and str(item.get("content") or "").strip()
        ]

    def _format_agent_knowledge_docs(self, docs: list[KnowledgeDoc]) -> list[str]:
        if not docs:
            return []
        lines = ["## RAG 知识库资料"]
        for doc in docs:
            lines.append(f"### {doc.title}")
            lines.append(doc.content)
            if doc.source:
                lines.append(f"*来源: {doc.source}*")
        lines.append("")
        lines.append("## RAG 使用要求")
        lines.append("生成内容必须优先依据以上知识库资料；涉及事实、地点、产品、业务、数据或资质时，不得编造知识库未提供的信息。")
        return lines

    def _append_knowledge_context_to_instruction(self, instruction: str, docs: list[KnowledgeDoc]) -> str:
        context_lines = self._format_agent_knowledge_docs(docs)
        if not context_lines:
            return instruction
        return "\n".join([instruction, "", *context_lines])

    def _request_with_retrieved_context(
        self,
        request: AgentChatRequest,
        retrieved_context: list[Any],
    ) -> AgentChatRequest:
        docs = self._knowledge_docs_from_retrieved_context(
            [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in retrieved_context
            ]
        )
        if not docs:
            return request
        context = request.context or AgentContext()
        merged = context.model_copy(update={"knowledge_docs": [*context.knowledge_docs, *docs]})
        return request.model_copy(update={"context": merged})

    def _build_chat_prompt(
        self,
        request: AgentChatRequest,
        retrieved_context: list[Any] | None = None,
    ) -> str:
        enriched_request = self._request_with_retrieved_context(request, retrieved_context or [])
        sections: list[str] = []
        if enriched_request.context and enriched_request.context.chat_history:
            sections.extend(
                [
                    "## 飞书群聊上下文",
                    *[f"{msg.role}: {msg.content}" for msg in enriched_request.context.chat_history],
                    "",
                ]
            )
        if enriched_request.context and enriched_request.context.knowledge_docs:
            sections.extend(self._format_agent_knowledge_docs(enriched_request.context.knowledge_docs))
            sections.append("")
        sections.extend(["## 当前问题", enriched_request.message])
        return "\n".join(sections)

    async def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        """Handle direct agent chat requests with intent-based routing."""
        intent = AgentIntent.CHAT
        plan = None
        trace_events = []
        try:
            request = await self._context_assembler.assemble(request, sync_service=self._sync_service)
            session_artifact = await self._get_session_artifact(request)
            editable_document = await self._get_editable_document(request)
            intent = await self._router.classify_chat_intent(request.message)
            current_artifact_operation = self._resolve_current_artifact_operation(session_artifact, request, intent)
            if current_artifact_operation == "docx":
                editable_document = session_artifact if session_artifact and session_artifact.kind == "docx" else editable_document
            current_ppt_update = current_artifact_operation == "ppt" or self._should_continue_current_ppt(session_artifact, request, intent)
            if current_ppt_update:
                intent = AgentIntent.PPT
            if current_artifact_operation == "board":
                intent = AgentIntent.BOARD

            should_execute_runtime_tools = (
                request.planning_enabled
                and (
                    intent == AgentIntent.DOCX
                    or (intent == AgentIntent.PPT and not current_ppt_update)
                    or (intent == AgentIntent.BOARD and current_artifact_operation != "board")
                )
                and current_artifact_operation != "docx"
                and not self._should_edit_current_document(editable_document, request, intent)
            )
            runtime_turn = await self._prepare_agent_turn(
                request,
                intent,
                session_artifact,
                execute_tools=should_execute_runtime_tools,
            )
            trace_events = runtime_turn.trace_events
            plan = runtime_turn.plan
            docx_tool_result = self._runtime_tool_result(runtime_turn, "docx")
            ppt_tool_result = self._runtime_tool_result(runtime_turn, "ppt")
            board_tool_result = self._runtime_tool_result(runtime_turn, "board")
            events_v1 = AgentEventProtocol.from_traces(trace_events)
            enriched_request = self._request_with_retrieved_context(request, runtime_turn.retrieved_context)

            if current_artifact_operation == "docx" and editable_document is not None:
                plan = self._build_document_edit_plan(request.message) if request.planning_enabled else None
                self._replace_plan_trace(trace_events, plan)
                response = await self._edit_current_document(request, editable_document, plan=plan)
                response.events = self._events_from_traces(trace_events)
                await self._publish_chat_result(request, response)
                return response
            if current_ppt_update and request.planning_enabled:
                plan = self._build_current_artifact_edit_plan("ppt", request.message)
                self._replace_plan_trace(trace_events, plan)
            if current_artifact_operation == "board" and request.planning_enabled:
                plan = self._build_current_artifact_edit_plan("board", request.message)
                self._replace_plan_trace(trace_events, plan)
            if self._should_edit_current_document(editable_document, request, intent):
                plan = self._build_document_edit_plan(request.message) if request.planning_enabled else None
                self._replace_plan_trace(trace_events, plan)
                response = await self._edit_current_document(request, editable_document, plan=plan)
                response.events = self._events_from_traces(trace_events)
                await self._publish_chat_result(request, response)
                return response

            events_v1 = self._events_from_traces(trace_events)

            if plan is not None and (plan.clarification_needed or plan.need_clarification):
                question = plan.clarification_question or (plan.questions[0] if plan.questions else None)
                if question:
                    response = AgentChatResponse(
                        session_id=request.session_id,
                        intent=intent.value,
                        status="completed",
                        message=question,
                        plan=plan,
                        events=events_v1,
                    )
                    await self._publish_chat_result(request, response)
                    return response

            if intent == AgentIntent.DOCX:
                content = (
                    str(docx_tool_result.get("content"))
                    if docx_tool_result is not None and docx_tool_result.get("content") is not None
                    else await self._generate_document_with_realtime_stream(enriched_request)
                )
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.DOCX.value,
                    status="completed",
                    message="文档生成完成。",
                    artifact=AgentChatArtifact(
                        kind="docx",
                        content=content,
                    ),
                    plan=plan,
                    events=events_v1,
                )
                synced_url = await self._sync_document_to_feishu_chat(request, content)
                if synced_url and response.artifact is not None:
                    response.message = "文档生成完成，并已同步到飞书。"
                    response.artifact.sharing_url = synced_url
                await self._publish_chat_result(request, response)
                return response

            if intent == AgentIntent.PPT:
                if self._aippt_service is None:
                    raise RuntimeError("aippt_service is not configured")
                is_current_ppt_update = current_ppt_update and self._load_current_ppt_preview(session_artifact) is not None

                if ppt_tool_result is not None:
                    artifact = self._ppt_artifact_from_tool_result(ppt_tool_result)
                    job_id = artifact.job_id
                elif is_current_ppt_update:
                    design_mode = self._resolve_current_ppt_design_mode(session_artifact) or "template"
                    job = self._aippt_service.create_job_from_request(
                        PPTGenerationRequest(
                            topic=self._build_ppt_topic(
                                enriched_request,
                                session_artifact=session_artifact,
                            ),
                            page_count=self._resolve_ppt_page_count(
                                enriched_request,
                                session_artifact=session_artifact,
                            ),
                            style="clean_business",
                            design_mode=design_mode,
                        )
                    )
                    artifact = self._ppt_artifact_from_job(job)
                    job_id = job.job_id
                else:
                    # Planner didn't call the ppt tool — let LLM generate a response
                    chat_prompt = self._build_chat_prompt(request, runtime_turn.retrieved_context)
                    reply = await self._llm.generate(
                        "你是 Eko 智能办公助手。请直接、友好地回答用户问题。若 RAG 知识库资料与问题相关，必须优先依据知识库资料回答；不要编造知识库未提供的信息。",
                        chat_prompt,
                    )
                    response = AgentChatResponse(
                        session_id=request.session_id,
                        intent=AgentIntent.PPT.value,
                        status="completed",
                        message=reply,
                        plan=plan,
                        events=events_v1,
                    )
                    await self._publish_chat_result(request, response)
                    return response

                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.PPT.value,
                    status="completed",
                    message=(
                        "AI PPT 更新任务已创建，正在保留原结构并修改指定页面。"
                        if is_current_ppt_update
                        else "AI PPT 任务已创建，正在后台生成。"
                    ),
                    artifact=artifact,
                    plan=plan,
                    events=events_v1,
                )
                await self._publish_ppt_job_started(request, response)
                if job_id:
                    self._schedule_ppt_job(request, job_id)
                return response

            if intent == AgentIntent.BOARD:
                sharing_url = self._resolve_board_sharing_url(request, session_artifact)
                created_board_document: dict[str, str] | None = None
                await self._publish_board_task_started(request, sharing_url=sharing_url)

                if board_tool_result is None:
                    if not sharing_url:
                        created_board_document = await self._feishu.create_board_document(
                            title=f"Eko 画板 - {request.message[:24]}",
                        )
                        sharing_url = created_board_document["sharing_url"]
                    board_instruction = self._append_knowledge_context_to_instruction(
                        request.message,
                        enriched_request.context.knowledge_docs if enriched_request.context else [],
                    )
                    board_task = self._canvas_service.create_board_task(
                        CanvasBoardTaskCreateRequest(
                            message=board_instruction,
                            sharing_url=sharing_url,
                        )
                    )
                    completed_task = self._canvas_service.run_board_task(board_task.task_id)
                else:
                    maybe_created = board_tool_result.get("created_board_document")
                    if isinstance(maybe_created, dict):
                        created_board_document = {str(key): str(value) for key, value in maybe_created.items()}
                        sharing_url = sharing_url or created_board_document.get("sharing_url")
                    completed_task = CanvasBoardTaskSchema(**board_tool_result)
                is_failed = completed_task.status == "failed"
                result_summary = completed_task.result_summary
                if created_board_document is not None and not is_failed:
                    result_summary = f"已自动创建飞书文档并生成画板：{completed_task.result_summary or sharing_url}"
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.BOARD.value,
                    status="failed" if is_failed else "completed",
                    message=completed_task.error_message if is_failed else "飞书画板任务已完成。",
                    artifact=AgentChatArtifact(
                        kind="board",
                        task_id=completed_task.task_id,
                        status=completed_task.status,
                        render_mode=completed_task.render_mode,
                        whiteboard_id=completed_task.whiteboard_id,
                        preview_url=completed_task.preview_url,
                        ticket_id=completed_task.ticket_id,
                        node_ids=completed_task.node_ids,
                        deleted_count=completed_task.deleted_count,
                        sharing_url=completed_task.sharing_url or sharing_url,
                        result_summary=result_summary,
                        error_message=completed_task.error_message,
                    ),
                    plan=plan,
                    events=events_v1,
                    error=completed_task.error_message if is_failed else None,
                )
                if created_board_document is not None and not is_failed:
                    await self._share_board_result_to_feishu_chat(request, created_board_document, completed_task)
                await self._publish_chat_result(request, response)
                return response

            chat_prompt = self._build_chat_prompt(request, runtime_turn.retrieved_context)

            reply = await self._llm.generate(
                "你是 Eko 智能办公助手。请直接、友好地回答用户问题。若 RAG 知识库资料与问题相关，必须优先依据知识库资料回答；不要编造知识库未提供的信息。",
                chat_prompt,
            )
            response = AgentChatResponse(
                session_id=request.session_id,
                intent=AgentIntent.CHAT.value,
                status="completed",
                message=reply,
                plan=plan,
                events=events_v1,
            )
            await self._publish_chat_result(request, response)
            return response

        except Exception as exc:  # noqa: BLE001
            logger.error("Agent chat failed session=%s, error=%s", request.session_id, exc)
            response_intent = intent if intent in {
                AgentIntent.CHAT,
                AgentIntent.DOCX,
                AgentIntent.PPT,
                AgentIntent.BOARD,
            } else AgentIntent.CHAT
            response = AgentChatResponse(
                session_id=request.session_id,
                intent=response_intent.value,
                status="failed",
                message="处理失败，请稍后重试",
                plan=plan,
                events=AgentEventProtocol.from_traces(trace_events),
                error=str(exc),
            )
            await self._publish_chat_result(request, response)
            return response

    async def chat_stream_events(self, request: AgentChatRequest) -> AsyncIterator[dict[str, Any]]:
        """Stream visible agent reasoning/planning/tool progress for chat requests."""
        intent = AgentIntent.CHAT
        plan = None
        trace_events = []
        yield AgentEventProtocol.start(request.planning_enabled)

        try:
            request = await self._context_assembler.assemble(request, sync_service=self._sync_service)
            session_artifact = await self._get_session_artifact(request)
            editable_document = await self._get_editable_document(request)
            intent = await self._router.classify_chat_intent(request.message)
            current_artifact_operation = self._resolve_current_artifact_operation(session_artifact, request, intent)
            if current_artifact_operation == "docx":
                editable_document = session_artifact if session_artifact and session_artifact.kind == "docx" else editable_document
                if editable_document is not None:
                    intent = AgentIntent.DOCX
            current_ppt_update = current_artifact_operation == "ppt" or self._should_continue_current_ppt(session_artifact, request, intent)
            if current_ppt_update:
                intent = AgentIntent.PPT
            if current_artifact_operation == "board":
                intent = AgentIntent.BOARD
            if self._should_edit_current_document(editable_document, request, intent):
                intent = AgentIntent.DOCX
                yield AgentEventProtocol.intent(intent.value, "我判断这次是修改当前文档，不会重新生成文档。")
                if request.planning_enabled:
                    plan = self._build_document_edit_plan(request.message)
                    yield AgentEventProtocol.plan(plan, "规划完成。下面直接修改当前文档。")
                    async for event in self._stream_plan_progress(plan):
                        yield event
                yield AgentEventProtocol.tool_started(intent.value, "docx_edit", "好的，我现在调用文档编辑能力，直接修改当前文档内容。")
                response = await self._edit_current_document(request, editable_document, plan=plan)
                await self._publish_chat_result(request, response)
                yield AgentEventProtocol.result(response, response.message)
                return

            if current_ppt_update or current_artifact_operation == "board":
                artifact_kind = "ppt" if current_ppt_update else "board"
                yield AgentEventProtocol.intent(
                    intent.value,
                    "我判断这次是修改当前 PPT，不会重新生成一份。"
                    if artifact_kind == "ppt"
                    else "我判断这次是修改当前飞书画板，不会新建画板文档。",
                )
                if request.planning_enabled:
                    plan = self._build_current_artifact_edit_plan(artifact_kind, request.message)
                    yield AgentEventProtocol.plan(plan, "规划完成。下面直接修改当前产物。")
                    async for event in self._stream_plan_progress(plan):
                        yield event
                yield AgentEventProtocol.tool_started(
                    intent.value,
                    "ppt_edit" if artifact_kind == "ppt" else "board_edit",
                    "好的，我现在调用 AI PPT 编辑能力，保留原结构并修改指定页面。"
                    if artifact_kind == "ppt"
                    else "好的，我现在调用飞书画板编辑能力，基于当前画板执行修改。",
                )
                execution_request = request.model_copy(update={"planning_enabled": False})
                response = await self.chat(execution_request)
                response.plan = plan
                yield AgentEventProtocol.result(response, response.message)
                return

            yield AgentEventProtocol.intent(intent.value)

            runtime_turn = await self._prepare_agent_turn(
                request,
                intent,
                session_artifact,
                execute_tools=(
                    request.planning_enabled
                    and (
                        intent == AgentIntent.DOCX
                        or (intent == AgentIntent.PPT and not current_ppt_update)
                        or (intent == AgentIntent.BOARD and current_artifact_operation != "board")
                    )
                ),
            )
            trace_events = runtime_turn.trace_events
            for trace_event in trace_events:
                if trace_event.type in {"retrieval_started", "retrieval_completed"}:
                    yield AgentEventProtocol.from_trace(trace_event).model_dump()
            runtime_plan = runtime_turn.plan
            docx_tool_result = self._runtime_tool_result(runtime_turn, "docx")
            ppt_tool_result = self._runtime_tool_result(runtime_turn, "ppt")
            board_tool_result = self._runtime_tool_result(runtime_turn, "board")

            if request.planning_enabled:
                plan = runtime_plan or await self._create_plan_with_timeout(request, intent)
                yield AgentEventProtocol.plan(plan, "规划完成。下面按这些子任务执行。")
                async for event in self._stream_plan_progress(plan):
                    yield event
                if plan.need_clarification:
                    question = plan.clarification_question or (plan.questions[0] if plan.questions else None) or "请补充更多信息。"
                    yield AgentEventProtocol.clarification(intent.value, plan, question)
                    response = AgentChatResponse(
                        session_id=request.session_id,
                        intent=intent.value,
                        status="completed",
                        message=question,
                        plan=plan,
                        events=self._events_from_traces(trace_events),
                    )
                    await self._publish_chat_result(request, response)
                    yield AgentEventProtocol.result(response, response.message)
                    return

            yield AgentEventProtocol.tool_started(intent.value, intent.value, self._tool_call_message(intent))

            if intent == AgentIntent.DOCX and docx_tool_result is not None and docx_tool_result.get("content") is not None:
                content = str(docx_tool_result["content"])
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.DOCX.value,
                    status="completed",
                    message="文档生成完成。",
                    artifact=AgentChatArtifact(kind="docx", content=content),
                    plan=plan,
                    events=self._events_from_traces(trace_events),
                )
                synced_url = await self._sync_document_to_feishu_chat(request, content)
                if synced_url and response.artifact is not None:
                    response.message = "文档生成完成，并已同步到飞书。"
                    response.artifact.sharing_url = synced_url
                await self._publish_chat_result(request, response)
            elif intent == AgentIntent.PPT and ppt_tool_result is not None:
                artifact = self._ppt_artifact_from_tool_result(ppt_tool_result)
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.PPT.value,
                    status="completed",
                    message="AI PPT 任务已创建，正在后台生成。",
                    artifact=artifact,
                    plan=plan,
                    events=self._events_from_traces(trace_events),
                )
                await self._publish_ppt_job_started(request, response)
                if artifact.job_id:
                    self._schedule_ppt_job(request, artifact.job_id)
            elif intent == AgentIntent.BOARD and board_tool_result is not None:
                created_board_document = None
                maybe_created = board_tool_result.get("created_board_document")
                if isinstance(maybe_created, dict):
                    created_board_document = {str(key): str(value) for key, value in maybe_created.items()}
                completed_task = CanvasBoardTaskSchema(**board_tool_result)
                is_failed = completed_task.status == "failed"
                result_summary = completed_task.result_summary
                if created_board_document is not None and not is_failed:
                    result_summary = f"已自动创建飞书文档并生成画板：{completed_task.result_summary or completed_task.sharing_url}"
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.BOARD.value,
                    status="failed" if is_failed else "completed",
                    message=completed_task.error_message if is_failed else "飞书画板任务已完成。",
                    artifact=AgentChatArtifact(
                        kind="board",
                        task_id=completed_task.task_id,
                        status=completed_task.status,
                        render_mode=completed_task.render_mode,
                        whiteboard_id=completed_task.whiteboard_id,
                        preview_url=completed_task.preview_url,
                        ticket_id=completed_task.ticket_id,
                        node_ids=completed_task.node_ids,
                        deleted_count=completed_task.deleted_count,
                        sharing_url=completed_task.sharing_url,
                        result_summary=result_summary,
                        error_message=completed_task.error_message,
                    ),
                    plan=plan,
                    events=self._events_from_traces(trace_events),
                    error=completed_task.error_message if is_failed else None,
                )
                if created_board_document is not None and not is_failed:
                    await self._share_board_result_to_feishu_chat(request, created_board_document, completed_task)
                await self._publish_chat_result(request, response)
            elif intent == AgentIntent.CHAT:
                reply = await self._llm.generate(
                    "你是 Eko 智能办公助手。请直接、友好地回答用户问题。若 RAG 知识库资料与问题相关，必须优先依据知识库资料回答；不要编造知识库未提供的信息。",
                    self._build_chat_prompt(request, runtime_turn.retrieved_context),
                )
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.CHAT.value,
                    status="completed",
                    message=reply,
                    plan=plan,
                    events=self._events_from_traces(trace_events),
                )
                await self._publish_chat_result(request, response)
            else:
                execution_request = request.model_copy(update={"planning_enabled": False})
                response = await self.chat(execution_request)
                response.plan = plan
            yield AgentEventProtocol.result(response, response.message)
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent chat stream failed session=%s, error=%s", request.session_id, exc)
            response = AgentChatResponse(
                session_id=request.session_id,
                intent=intent.value,
                status="failed",
                message="处理失败，请稍后重试",
                plan=plan,
                events=AgentEventProtocol.from_traces(trace_events),
                error=str(exc),
            )
            yield AgentEventProtocol.failed(response, response.message, str(exc))

    async def _stream_plan_progress(self, plan: AgentTaskPlan) -> AsyncIterator[dict[str, Any]]:
        for event in AgentEventProtocol.plan_progress(plan):
            yield event

    def _wants_new_document(self, message: str) -> bool:
        normalized = message.lower()
        return any(keyword in message or keyword in normalized for keyword in (*_NEW_DOCUMENT_KEYWORDS, *_ARTIFACT_CREATE_KEYWORDS))

    def _looks_like_current_artifact_edit(self, message: str) -> bool:
        normalized = message.lower()
        if any(keyword in message or keyword in normalized for keyword in _ARTIFACT_CREATE_KEYWORDS):
            return False
        if re.search(r"第\s*(?:\d+|[一二两三四五六七八九十])\s*(?:页|张|个|块|节点|部分)", message):
            return True
        if re.search(r"(这一|这|当前)(?:页|张|段|部分|节点|块|个|份|版)", message):
            return True
        return any(keyword in message or keyword in normalized for keyword in _ARTIFACT_EDIT_KEYWORDS)

    def _resolve_current_artifact_operation(
        self,
        session_artifact: AgentChatArtifact | None,
        request: AgentChatRequest,
        intent: AgentIntent,
    ) -> str | None:
        if session_artifact is None or self._wants_new_document(request.message):
            return None
        if session_artifact.kind not in {"docx", "ppt", "board"}:
            return None
        if not self._looks_like_current_artifact_edit(request.message):
            return None

        if session_artifact.kind == "docx":
            if session_artifact.content:
                return "docx"
            return None
        if session_artifact.kind == "ppt":
            if intent == AgentIntent.BOARD:
                return None
            return "ppt"
        if session_artifact.kind == "board":
            if intent in {AgentIntent.DOCX, AgentIntent.PPT}:
                return None
            return "board"
        return None

    def _should_edit_current_document(
        self,
        editable_document: AgentChatArtifact | None,
        request: AgentChatRequest,
        intent: AgentIntent,
    ) -> bool:
        if editable_document is None:
            return False
        if self._wants_new_document(request.message):
            return False
        if intent in {AgentIntent.PPT, AgentIntent.BOARD}:
            return False
        return intent in {AgentIntent.CHAT, AgentIntent.DOCX}

    def _should_continue_current_ppt(
        self,
        session_artifact: AgentChatArtifact | None,
        request: AgentChatRequest,
        intent: AgentIntent,
    ) -> bool:
        if session_artifact is None or session_artifact.kind != "ppt":
            return False
        if intent in {AgentIntent.PPT, AgentIntent.BOARD}:
            return False
        if not self._looks_like_current_artifact_edit(request.message):
            return False
        normalized = request.message.lower()
        explicit_docx = any(keyword in request.message or keyword in normalized for keyword in ("文档", "报告", "方案", "docx", "document"))
        if explicit_docx:
            return False
        return True

    def _resolve_board_sharing_url(
        self,
        request: AgentChatRequest,
        session_artifact: AgentChatArtifact | None,
    ) -> str | None:
        if request.sharing_url:
            return request.sharing_url
        if session_artifact is not None and session_artifact.kind == "board":
            return session_artifact.sharing_url
        return None

    async def _get_session_artifact(self, request: AgentChatRequest) -> AgentChatArtifact | None:
        if request.current_document is not None:
            return request.current_document
        if self._sync_service is None or not hasattr(self._sync_service, "get_session"):
            return None
        session = await self._sync_service.get_session(request.session_id)
        if session is None or not isinstance(session.artifact, dict):
            return None
        try:
            return AgentChatArtifact(**session.artifact)
        except Exception:  # noqa: BLE001
            return None

    async def _get_editable_document(self, request: AgentChatRequest) -> AgentChatArtifact | None:
        artifact = request.current_document
        if artifact is not None and artifact.kind == "docx" and artifact.content:
            return artifact

        if self._sync_service is None:
            return None
        if not hasattr(self._sync_service, "get_session"):
            return None
        session = await self._sync_service.get_session(request.session_id)
        if session is None or not isinstance(session.artifact, dict):
            return None
        try:
            candidate = AgentChatArtifact(**session.artifact)
        except Exception:  # noqa: BLE001
            return None
        if candidate.kind != "docx" or not candidate.content:
            return None
        return candidate

    def _build_document_edit_plan(self, message: str) -> AgentTaskPlan:
        return AgentTaskPlan(
            goal="修改当前会话中的已有文档",
            intent="document_editing",
            task_complexity="simple",
            missing_info=[],
            need_clarification=False,
            questions=[],
            assumptions=["使用当前会话里已经生成的文档作为编辑对象"],
            summary="定位当前文档内容，按用户要求执行局部编辑，并更新文档预览。",
            visible_summary="我理解你要修改当前文档。我会先确认编辑对象，再按你的要求局部修改，最后更新当前预览。",
            tool_candidates=["docx_edit", "sync"],
            steps=[
                AgentPlanStep(
                    id="step_1",
                    title="确认编辑对象",
                    description="读取当前会话中已有的 docx 文档内容和链接。",
                    type="reasoning",
                    tool=None,
                    input={"source": "current_document"},
                    expected_output="待编辑的当前文档",
                    depends_on=[],
                ),
                AgentPlanStep(
                    id="step_2",
                    title="执行局部修改",
                    description=f"根据用户要求修改文档：{message}",
                    type="tool_call",
                    tool="docx_edit",
                    input={"instruction": message},
                    expected_output="修改后的 Markdown 文档",
                    depends_on=["step_1"],
                ),
                AgentPlanStep(
                    id="step_3",
                    title="更新会话产物",
                    description="将修改后的内容写回当前会话 artifact，刷新前端文档预览。",
                    type="validation",
                    tool="sync",
                    input={},
                    expected_output="可继续编辑的当前文档",
                    depends_on=["step_2"],
                ),
            ],
            final_output=AgentPlanFinalOutput(format="updated_markdown_document", requirements=["保留原文档无关内容", "不重新生成文档"]),
        )

    def _build_current_artifact_edit_plan(self, artifact_kind: str, message: str) -> AgentTaskPlan:
        if artifact_kind == "ppt":
            return AgentTaskPlan(
                goal="修改当前会话中的已有 PPT",
                intent="ppt_editing",
                task_complexity="medium",
                missing_info=[],
                need_clarification=False,
                questions=[],
                assumptions=["使用当前会话里已经生成的 PPT 作为编辑对象"],
                summary="读取当前 PPT 结构，定位用户要改的页面，只重写指定页面并复用其他页面。",
                visible_summary="我理解你要修改当前 PPT。我会读取当前 PPT 结构，只处理你点名的页面，其他页面保持不变。",
                tool_candidates=["artifact_lookup", "ppt_edit", "sync"],
                steps=[
                    AgentPlanStep(
                        id="step_1",
                        title="确认当前 PPT",
                        description="读取当前会话的 PPT job、页数、页面标题和每页要点。",
                        type="reasoning",
                        tool=None,
                        input={"source": "current_ppt"},
                        expected_output="待编辑的当前 PPT",
                        depends_on=[],
                    ),
                    AgentPlanStep(
                        id="step_2",
                        title="解析修改意图",
                        description=f"理解用户要修改的页面、范围和内容：{message}",
                        type="reasoning",
                        tool=None,
                        input={"instruction": message},
                        expected_output="目标页和修改动作",
                        depends_on=["step_1"],
                    ),
                    AgentPlanStep(
                        id="step_3",
                        title="执行 PPT 局部编辑",
                        description="调用 AI PPT 编辑能力，仅重新生成目标页，未指定页面保持原样。",
                        type="tool_call",
                        tool="ppt_edit",
                        input={"instruction": message},
                        expected_output="更新后的 PPT job",
                        depends_on=["step_2"],
                    ),
                    AgentPlanStep(
                        id="step_4",
                        title="刷新预览",
                        description="更新会话 artifact，让前端预览和下载链接指向新的 PPT。",
                        type="validation",
                        tool="sync",
                        input={},
                        expected_output="可继续编辑的当前 PPT",
                        depends_on=["step_3"],
                    ),
                ],
                final_output=AgentPlanFinalOutput(format="updated_ppt", requirements=["只修改指定页面", "保留未指定页面", "不新建无关 PPT"]),
            )
        if artifact_kind == "board":
            return AgentTaskPlan(
                goal="修改当前会话中的已有飞书画板",
                intent="board_editing",
                task_complexity="medium",
                missing_info=[],
                need_clarification=False,
                questions=[],
                assumptions=["使用当前会话里已经存在的飞书画板链接作为编辑对象"],
                summary="读取当前画板链接，理解用户要改的节点或结构，并在原画板上执行修改。",
                visible_summary="我理解你要修改当前飞书画板。我会复用当前画板链接，定位要修改的节点或结构，再同步结果。",
                tool_candidates=["artifact_lookup", "board", "sync"],
                steps=[
                    AgentPlanStep(
                        id="step_1",
                        title="确认当前画板",
                        description="读取当前会话 artifact 中的飞书画板链接和 whiteboard 信息。",
                        type="reasoning",
                        tool=None,
                        input={"source": "current_board"},
                        expected_output="待编辑的当前画板",
                        depends_on=[],
                    ),
                    AgentPlanStep(
                        id="step_2",
                        title="解析画板修改",
                        description=f"理解用户要修改的节点、文字或结构：{message}",
                        type="reasoning",
                        tool=None,
                        input={"instruction": message},
                        expected_output="画板修改动作",
                        depends_on=["step_1"],
                    ),
                    AgentPlanStep(
                        id="step_3",
                        title="执行画板编辑",
                        description="调用飞书画板能力，在当前画板链接上执行修改。",
                        type="tool_call",
                        tool="board_edit",
                        input={"instruction": message},
                        expected_output="更新后的画板",
                        depends_on=["step_2"],
                    ),
                    AgentPlanStep(
                        id="step_4",
                        title="同步结果",
                        description="更新会话 artifact，让后续自然语言继续基于同一个画板修改。",
                        type="validation",
                        tool="sync",
                        input={},
                        expected_output="可继续编辑的当前画板",
                        depends_on=["step_3"],
                    ),
                ],
                final_output=AgentPlanFinalOutput(format="updated_board", requirements=["复用当前画板", "不自动新建画板文档"]),
        )
        return self._build_document_edit_plan(message)



    async def _edit_current_document(
        self,
        request: AgentChatRequest,
        artifact: AgentChatArtifact,
        *,
        plan: AgentTaskPlan | None = None,
    ) -> AgentChatResponse:
        edited_content = await self._document_service.edit_document(
            DocumentEditRequest(
                session_id=request.session_id,
                instruction=request.message,
                current_content=artifact.content or "",
                title=self._build_feishu_doc_title(request, "Eko 文档"),
            )
        )
        updated_artifact = artifact.model_copy(
            update={
                "kind": "docx",
                "content": edited_content,
                "status": "completed",
                "current_step": "文档已修改",
                "result_summary": "已按要求修改当前文档。",
            }
        )
        synced_url = await self._sync_document_to_feishu_chat(
            request,
            edited_content,
            chat_message_prefix="Eko 已更新飞书文档：",
        )
        message = "已修改当前文档。"
        if synced_url:
            updated_artifact = updated_artifact.model_copy(update={"sharing_url": synced_url})
            message = "已修改当前文档，并已同步到飞书。"
        return AgentChatResponse(
            session_id=request.session_id,
            intent=AgentIntent.DOCX.value,
            status="completed",
            message=message,
            artifact=updated_artifact,
            plan=plan,
        )

    def _tool_call_message(self, intent: AgentIntent) -> str:
        if intent == AgentIntent.DOCX:
            return "好的，我现在调用文档生成能力，生成内容并同步到飞书。"
        if intent == AgentIntent.PPT:
            return "好的，我现在调用 AI PPT 能力，创建生成任务并等待导出。"
        if intent == AgentIntent.BOARD:
            return "好的，我现在调用飞书画板能力，把任务落到画板流程里。"
        return "好的，我现在直接回复这个问题。"

    def _extract_feishu_chat_id(self, session_id: str) -> str | None:
        parts = session_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "feishu":
            return None
        return parts[1] or None

    def _build_feishu_doc_title(self, request: AgentChatRequest, prefix: str) -> str:
        normalized = " ".join(request.message.split())
        return f"{prefix} - {normalized[:24]}" if normalized else prefix

    def _extract_docx_token_from_url(self, document_url: str) -> str | None:
        parsed = urlparse(document_url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        if len(segments) >= 2 and segments[-2] == "docx":
            return segments[-1]
        return None

    def _build_document_request(self, request: AgentChatRequest) -> DocumentGenerationRequest:
        return DocumentGenerationRequest(
            session_id=request.session_id,
            topic=request.message,
            requirement=request.message,
            chat_history=[
                DocumentChatMessage(role=msg.role, content=msg.content)
                for msg in (request.context.chat_history if request.context else [])
            ],
            knowledge_docs=[
                DocumentKnowledgeDoc(title=doc.title, content=doc.content, source=doc.source)
                for doc in (request.context.knowledge_docs if request.context else [])
            ],
            bitable_records=[
                DocumentBitableRecord(table_name=record.table_name, fields=record.fields)
                for record in (request.context.bitable_records if request.context else [])
            ],
        )

    async def _generate_document_with_realtime_stream(self, request: AgentChatRequest) -> str:
        document_request = self._build_document_request(request)
        if self._sync_service is None:
            return await self._document_service.generate_document(document_request)

        started_artifact = AgentChatArtifact(
            kind="docx",
            content="",
            status="running",
            current_step="生成文档",
        )
        await self._sync_service.publish_task_completed(
            request.session_id,
            intent=AgentIntent.DOCX.value,
            message="文档生成已启动。",
            status="进行中",
            artifact=started_artifact.model_dump(),
            messages=await self._build_merged_sync_messages(
                request,
                AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.DOCX.value,
                    status="completed",
                    message="文档生成已启动。",
                    artifact=started_artifact,
                ),
            ),
        )
        chunks: list[str] = []
        async for chunk in self._document_service.generate_document_stream(document_request):
            for piece in self._split_typewriter_chunk(chunk):
                chunks.append(piece)
                await self._sync_service.publish_document_stream_chunk(
                    request.session_id,
                    content="".join(chunks),
                    chunk=piece,
                )
        content = "".join(chunks)
        grounded_content = self._document_service.ground_document_if_needed(document_request, content)
        if grounded_content != content:
            await self._sync_service.publish_document_stream_chunk(
                request.session_id,
                content=grounded_content,
                chunk=grounded_content,
            )
        return grounded_content

    def _split_typewriter_chunk(self, chunk: str) -> list[str]:
        if not chunk:
            return []
        return [chunk]

    async def _sync_document_to_feishu_chat(
        self,
        request: AgentChatRequest,
        content: str,
        *,
        chat_message_prefix: str = "Eko 已创建飞书文档：",
    ) -> str | None:
        chat_id = self._extract_feishu_chat_id(request.session_id)
        if chat_id is None:
            return None

        try:
            result = await self._feishu.publish_markdown_to_feishu(
                title=self._build_feishu_doc_title(request, "Eko 文档"),
                markdown_content=content,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sync generated docx to Feishu failed session=%s: %s", request.session_id, exc)
            return None

        document_url = result.get("document_url")
        if not isinstance(document_url, str) or not document_url:
            return None

        document_id = self._extract_docx_token_from_url(document_url)
        if document_id:
            try:
                await self._feishu.add_docx_permission_for_chat(document_id, chat_id, perm="edit")
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Grant generated docx permission to Feishu chat failed session=%s doc=%s chat=%s: %s",
                    request.session_id,
                    document_id,
                    chat_id,
                    exc,
                )

        try:
            await self._feishu.send_text_message_to_chat(
                chat_id,
                f"{chat_message_prefix}\n{document_url}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Send generated docx link to Feishu chat failed session=%s: %s", request.session_id, exc)
        return document_url

    async def _share_board_result_to_feishu_chat(
        self,
        request: AgentChatRequest,
        created_board_document: dict[str, str],
        completed_task: Any,
    ) -> None:
        chat_id = self._extract_feishu_chat_id(request.session_id)
        if chat_id is None:
            return

        document_id = created_board_document.get("document_id")
        sharing_url = created_board_document.get("sharing_url") or getattr(completed_task, "sharing_url", None)
        whiteboard_id = (
            getattr(completed_task, "whiteboard_id", None)
            or created_board_document.get("whiteboard_id")
        )

        if document_id:
            try:
                await self._feishu.add_docx_permission_for_chat(document_id, chat_id, perm="edit")
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Grant board docx permission to Feishu chat failed session=%s doc=%s chat=%s: %s",
                    request.session_id,
                    document_id,
                    chat_id,
                    exc,
                )

        if not sharing_url:
            return
        message = f"Eko 已创建飞书画板文档并完成生成：\n{sharing_url}"
        if whiteboard_id:
            message = f"{message}\n画板 ID：{whiteboard_id}"
        try:
            await self._feishu.send_text_message_to_chat(chat_id, message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Send board link to Feishu chat failed session=%s: %s", request.session_id, exc)

    def _resolve_ppt_page_count(
        self,
        request: AgentChatRequest,
        *,
        session_artifact: AgentChatArtifact | None = None,
    ) -> int:
        current_ppt = self._load_current_ppt_preview(session_artifact)
        page_count = current_ppt.get("page_count") if current_ppt else None
        if isinstance(page_count, int) and 1 <= page_count <= 20 and self._is_current_ppt_edit_message(request.message):
            return page_count

        explicit_page_count = self._extract_ppt_page_count(request.message)
        if explicit_page_count != 6:
            return explicit_page_count
        if isinstance(page_count, int) and 1 <= page_count <= 20:
            return page_count
        return explicit_page_count

    def _is_current_ppt_edit_message(self, message: str) -> bool:
        if any(keyword in message for keyword in ("新建", "重新生成", "再生成一份", "生成一份", "生成一个")):
            return False
        return any(
            keyword in message
            for keyword in (
                "改",
                "修改",
                "调整",
                "替换",
                "删除",
                "第一页",
                "第1页",
                "第二页",
                "第2页",
                "第三页",
                "第3页",
                "第四页",
                "第4页",
                "第五页",
                "第5页",
                "第六页",
                "第6页",
            )
        )

    def _build_ppt_topic(
        self,
        request: AgentChatRequest,
        *,
        session_artifact: AgentChatArtifact | None = None,
    ) -> str:
        sections: list[str] = []
        current_ppt = self._load_current_ppt_preview(session_artifact)
        if current_ppt:
            sections.extend(self._format_current_ppt_context(current_ppt))
        if request.context and request.context.chat_history:
            sections.extend(
                [
                    "## 飞书群聊上下文",
                    *[f"{msg.role}: {msg.content}" for msg in request.context.chat_history],
                    "",
                ]
            )
        if current_ppt:
            sections.extend(
                [
                    "## 修改要求",
                    request.message,
                    "",
                    "## 生成要求",
                    "基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。",
                    "除用户明确要求修改的页面外，保留原 PPT 的主题、页数、页面顺序、标题和核心内容。",
                    "如果用户说“第一页/第三张/第 N 页”，只调整对应页面；没有点名的页面不要重写、不要删减。",
                ]
            )
            return "\n".join(sections)
        sections.extend(["## 当前指令", request.message])
        return "\n".join(sections)

    def _load_current_ppt_preview(self, session_artifact: AgentChatArtifact | None) -> dict[str, Any] | None:
        if (
            session_artifact is None
            or session_artifact.kind != "ppt"
            or not session_artifact.job_id
            or self._aippt_service is None
            or not hasattr(self._aippt_service, "get_preview")
        ):
            return None
        try:
            preview = self._aippt_service.get_preview(session_artifact.job_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Load current PPT preview failed job=%s: %s", session_artifact.job_id, exc)
            return None
        return preview if isinstance(preview, dict) else None

    def _resolve_current_ppt_design_mode(self, session_artifact: AgentChatArtifact | None) -> str | None:
        preview = self._load_current_ppt_preview(session_artifact)
        mode = preview.get("design_mode") if preview else None
        if mode in {"template", "free_design"}:
            return str(mode)
        return None

    def _format_current_ppt_context(self, preview: dict[str, Any]) -> list[str]:
        title = str(preview.get("title") or "当前 PPT")
        page_count = preview.get("page_count")
        slides = preview.get("slides") if isinstance(preview.get("slides"), list) else []
        lines = [
            "## 当前 PPT",
            f"标题：{title}",
            f"来源 Job：{preview.get('job_id')}" if preview.get("job_id") else "来源 Job：未知",
            f"页数：{page_count}" if page_count else "页数：未知",
        ]
        for slide in slides[:20]:
            if not isinstance(slide, dict):
                continue
            number = slide.get("slide_number") or slide.get("number") or "?"
            slide_title = str(slide.get("title") or f"第 {number} 页")
            items = slide.get("right_items") if isinstance(slide.get("right_items"), list) else []
            item_texts = []
            for item in items[:4]:
                if isinstance(item, dict):
                    text = item.get("title") or item.get("text") or item.get("content")
                    if text:
                        item_texts.append(str(text))
                elif item:
                    item_texts.append(str(item))
            suffix = f"；要点：{' / '.join(item_texts)}" if item_texts else ""
            lines.append(f"- 第 {number} 页：{slide_title}{suffix}")
        lines.append("")
        return lines

    async def _publish_board_task_started(
        self,
        request: AgentChatRequest,
        *,
        sharing_url: str | None,
    ) -> None:
        if self._sync_service is None:
            return
        artifact = AgentChatArtifact(
            kind="board",
            status="running",
            sharing_url=sharing_url,
            result_summary="正在创建飞书画板并生成内容。",
        )
        await self._sync_service.publish_task_completed(
            request.session_id,
            intent=AgentIntent.BOARD.value,
            message="飞书画板任务已启动。",
            status="进行中",
            artifact=artifact.model_dump(),
            messages=await self._build_merged_sync_messages(
                request,
                AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.BOARD.value,
                    status="completed",
                    message="飞书画板任务已启动。",
                    artifact=artifact,
                ),
            ),
        )

    def _ppt_artifact_from_job(self, job) -> AgentChatArtifact:
        return AgentChatArtifact(
            kind="ppt",
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            download_url=job.download_url,
            error_message=getattr(job, "error", None),
        )

    def _absolute_backend_url(self, path_or_url: str | None) -> str | None:
        if not path_or_url:
            return None
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
        if path_or_url.startswith("/"):
            host = settings.HOST if settings.HOST not in {"0.0.0.0", "::"} else "127.0.0.1"
            return f"http://{host}:{settings.PORT}{path_or_url}"
        return path_or_url

    def _build_ppt_share_markdown(
        self,
        request: AgentChatRequest,
        job: Any,
        *,
        preview: dict[str, Any] | None,
    ) -> str:
        title = str((preview or {}).get("title") or getattr(job, "source_name", None) or "AI PPT")
        page_count = (preview or {}).get("page_count") or getattr(job, "page_count", None)
        download_url = self._absolute_backend_url(getattr(job, "download_url", None))
        slides = (preview or {}).get("slides")
        slide_items = slides if isinstance(slides, list) else []

        lines = [
            f"# {title}",
            "",
            "这是 Eko 生成的 PPT 分享文档，用于在飞书中查看、转发和协作。",
            "",
            "## 生成信息",
            "",
            f"- 原始需求：{request.message}",
            f"- 页数：{page_count or len(slide_items) or '未知'}",
        ]
        if download_url:
            lines.append(f"- 下载 PPT：{download_url}")
        lines.extend(["", "## 幻灯片目录", ""])

        if not slide_items:
            lines.append("- PPT 已生成，可通过上方链接下载。")
            return "\n".join(lines)

        for index, slide in enumerate(slide_items[:30], start=1):
            if not isinstance(slide, dict):
                continue
            number = slide.get("slide_number") or slide.get("number") or index
            slide_title = str(slide.get("title") or f"第 {number} 页")
            lines.append(f"### 第 {number} 页：{slide_title}")
            description = slide.get("subtitle") or slide.get("description") or slide.get("body")
            if description:
                lines.append(str(description))
            right_items = slide.get("right_items") if isinstance(slide.get("right_items"), list) else []
            bullets: list[str] = []
            for item in right_items[:8]:
                if isinstance(item, dict):
                    text = item.get("title") or item.get("text") or item.get("content") or item.get("label")
                    detail = item.get("detail") or item.get("description")
                    if text and detail:
                        bullets.append(f"{text}：{detail}")
                    elif text:
                        bullets.append(str(text))
                elif item:
                    bullets.append(str(item))
            for bullet in bullets:
                lines.append(f"- {bullet}")
            lines.append("")
        return "\n".join(lines).strip()

    async def _sync_ppt_to_feishu_document(self, request: AgentChatRequest, job: Any) -> str | None:
        chat_id = self._extract_feishu_chat_id(request.session_id)
        if chat_id is None:
            return None

        preview: dict[str, Any] | None = None
        if self._aippt_service is not None and hasattr(self._aippt_service, "get_preview"):
            try:
                loaded_preview = await asyncio.to_thread(self._aippt_service.get_preview, job.job_id)
                preview = loaded_preview if isinstance(loaded_preview, dict) else None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Load completed PPT preview for Feishu share failed job=%s: %s", job.job_id, exc)

        title_source = str((preview or {}).get("title") or getattr(job, "source_name", None) or request.message)
        markdown = self._build_ppt_share_markdown(request, job, preview=preview)
        try:
            result = await self._feishu.publish_markdown_to_feishu(
                title=self._build_feishu_doc_title(request, f"Eko PPT - {title_source[:24]}"),
                markdown_content=markdown,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sync generated PPT to Feishu document failed session=%s job=%s: %s", request.session_id, job.job_id, exc)
            return None

        document_url = result.get("document_url")
        if not isinstance(document_url, str) or not document_url:
            return None

        document_id = self._extract_docx_token_from_url(document_url)
        if document_id:
            try:
                await self._feishu.add_docx_permission_for_chat(document_id, chat_id, perm="edit")
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Grant generated PPT share doc permission failed session=%s doc=%s chat=%s: %s",
                    request.session_id,
                    document_id,
                    chat_id,
                    exc,
                )

        try:
            await self._feishu.send_text_message_to_chat(
                chat_id,
                f"Eko 已创建飞书 PPT 分享文档：\n{document_url}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Send generated PPT share document link failed session=%s: %s", request.session_id, exc)
        return document_url

    def _ppt_artifact_from_tool_result(self, result: dict[str, Any]) -> AgentChatArtifact:
        return AgentChatArtifact(
            kind="ppt",
            job_id=str(result.get("job_id")) if result.get("job_id") else None,
            status=str(result.get("status")) if result.get("status") else None,
            progress=int(result.get("progress")) if isinstance(result.get("progress"), int) else None,
            current_step=str(result.get("current_step")) if result.get("current_step") else None,
            download_url=str(result.get("download_url")) if result.get("download_url") else None,
            error_message=str(result.get("error")) if result.get("error") else None,
        )

    async def _publish_ppt_job_started(
        self,
        request: AgentChatRequest,
        response: AgentChatResponse,
    ) -> None:
        if self._sync_service is None:
            return
        artifact = response.artifact.model_dump() if response.artifact is not None else None
        await self._sync_service.publish_task_completed(
            response.session_id,
            intent=response.intent,
            message=response.message,
            status="进行中",
            artifact=artifact,
            messages=await self._build_merged_sync_messages(request, response),
            error=response.error,
        )

    def _schedule_ppt_job(self, request: AgentChatRequest, job_id: str) -> None:
        task = asyncio.create_task(self._run_ppt_job_and_publish(request, job_id))
        task.add_done_callback(lambda finished: self._log_ppt_background_task(request.session_id, job_id, finished))

    def _log_ppt_background_task(self, session_id: str, job_id: str, task: asyncio.Task[Any]) -> None:
        try:
            task.result()
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("AIPPT background task crashed session=%s job_id=%s", session_id, job_id)

    async def _run_ppt_job_and_publish(self, request: AgentChatRequest, job_id: str) -> None:
        if self._aippt_service is None:
            return
        try:
            await asyncio.to_thread(self._aippt_service.enqueue_job, job_id)
            job = await self._wait_for_ppt_job(job_id)
            if job.status not in {"done", "failed"}:
                if self._sync_service is not None:
                    response = AgentChatResponse(
                        session_id=request.session_id,
                        intent=AgentIntent.PPT.value,
                        status="completed",
                        message="AI PPT 任务已提交，等待生成完成。",
                        artifact=self._ppt_artifact_from_job(job),
                    )
                    await self._sync_service.publish_task_completed(
                        request.session_id,
                        intent=response.intent,
                        message=response.message,
                        status="进行中",
                        artifact=response.artifact.model_dump() if response.artifact is not None else None,
                        messages=await self._build_merged_sync_messages(request, response),
                    )
                return

            artifact = self._ppt_artifact_from_job(job)
            if job.status == "done":
                sharing_url = await self._sync_ppt_to_feishu_document(request, job)
                if sharing_url:
                    artifact.sharing_url = sharing_url

            response = AgentChatResponse(
                session_id=request.session_id,
                intent=AgentIntent.PPT.value,
                status="completed" if job.status == "done" else "failed" if job.status == "failed" else "completed",
                message=(
                    "AI PPT 已生成，并已同步到飞书文档。"
                    if job.status == "done" and artifact.sharing_url
                    else "AI PPT 已生成。"
                    if job.status == "done"
                    else "AI PPT 生成失败，请稍后重试。"
                ),
                artifact=artifact,
                error=job.error if getattr(job, "status", "") == "failed" else None,
            )
            if response.status == "failed" and self._sync_service is not None:
                await self._sync_service.publish_task_completed(
                    request.session_id,
                    intent=response.intent,
                    message=response.message,
                    status="failed",
                    artifact=response.artifact.model_dump() if response.artifact is not None else None,
                    messages=await self._build_merged_sync_messages(request, response),
                    error=response.error,
                )
                return
            await self._publish_chat_result(request, response)
        except Exception as exc:  # noqa: BLE001
            logger.exception("AIPPT background job failed session=%s job_id=%s", request.session_id, job_id)
            if self._sync_service is not None:
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.PPT.value,
                    status="failed",
                    message="AI PPT 生成失败，请稍后重试。",
                    artifact=AgentChatArtifact(
                        kind="ppt",
                        job_id=job_id,
                        status="failed",
                        error_message=str(exc),
                    ),
                    error=str(exc),
                )
                await self._sync_service.publish_task_completed(
                    request.session_id,
                    intent=response.intent,
                    message=response.message,
                    status="failed",
                    artifact=response.artifact.model_dump() if response.artifact is not None else None,
                    messages=await self._build_merged_sync_messages(request, response),
                    error=response.error,
                )

    async def _wait_for_ppt_job(self, job_id: str) -> Any:
        if self._aippt_service is None:
            raise RuntimeError("aippt_service is not configured")
        job = await asyncio.to_thread(self._aippt_service.get_job, job_id)
        for _ in range(60):
            if job.status in {"done", "failed"}:
                return job
            await asyncio.sleep(1)
            job = await asyncio.to_thread(self._aippt_service.get_job, job_id)
        return job

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
