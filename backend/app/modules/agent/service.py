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
    AgentRequest,
    AgentResponse,
    AgentStatus,
    AgentTraceEvent,
    BitableRecord,
    ChatMessage,
    IntentCandidate,
    IntentClarificationOption,
    IntentRouteResult,
    KnowledgeDoc,
    SubagentType,
    SyncDocumentRequest,
    SyncDocumentResponse,
)
from app.modules.agent.context import AgentContextAssembler
from app.modules.agent.events import AgentEventProtocol
from app.modules.agent.rag import AgentRAGRetriever
from app.modules.agent.runtime import AgentRuntime
from app.modules.agent.tools import AgentToolRegistry
from app.modules.bitable.schemas import BitableArchiveRequest, BitableQueryRequest
from app.modules.bitable.service import BitableService
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
from app.modules.feishu.events import FeishuEventProcessor
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

_PPT_FREE_DESIGN_KEYWORDS = (
    "自由设计",
    "自由模式",
    "自由版式",
    "自由布局",
    "自由排版",
    "不要模板",
    "不用模板",
    "非模板",
    "创意设计",
    "强视觉",
    "视觉表现",
    "free_design",
    "free design",
    "free-design",
    "freeform",
    "creative_freeform",
)

_PPT_TEMPLATE_KEYWORDS = (
    "模板模式",
    "模板生成",
    "使用模板",
    "用模板",
    "template",
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
        route = await self.route_chat_intent(message)
        return AgentIntent(route.intent)

    async def route_chat_intent(
        self,
        message: str,
        *,
        current_artifact: AgentChatArtifact | None = None,
        forced_intent: str | None = None,
    ) -> IntentRouteResult:
        """Return a standard route result that can interrupt for clarification."""
        forced = (forced_intent or "").strip().lower()
        if forced in {"chat", "docx", "ppt", "board"}:
            intent = AgentIntent(forced)
            return IntentRouteResult(
                intent=intent.value,
                primary_tool=self._primary_tool_for_intent(intent, current_artifact=current_artifact, message=message),
                confidence=1.0,
                reason="forced_intent",
                candidates=[IntentCandidate(intent=intent.value, tool=self._primary_tool_for_intent(intent, current_artifact=current_artifact, message=message), confidence=1.0, reason="forced")],
            )

        local_intents = self._local_explicit_intents(message)
        model_route = await self._classify_chat_intent_with_model(message)
        if self._is_current_artifact_ambiguous(message, current_artifact):
            return self._clarification_route(
                message,
                question=f"这是要修改当前 {self._artifact_label(current_artifact)}，还是新建一个产物？",
                options=[
                    IntentClarificationOption(label=f"修改当前{self._artifact_label(current_artifact)}", intent=current_artifact.kind if current_artifact and current_artifact.kind in {"docx", "ppt", "board"} else "chat", tool=self._edit_tool_for_artifact(current_artifact)),
                    IntentClarificationOption(label="新建文档", intent="docx", tool="docx"),
                    IntentClarificationOption(label="新建 PPT", intent="ppt", tool="ppt"),
                    IntentClarificationOption(label="普通回复", intent="chat", tool="chat"),
                ],
                reason="当前产物编辑/新建意图不明确",
                candidates=self._candidate_list(local_intents, model_route),
            )

        if local_intents:
            intent = local_intents[0]
            return IntentRouteResult(
                intent=intent.value,
                primary_tool=self._primary_tool_for_intent(intent, current_artifact=current_artifact, message=message),
                confidence=0.95,
                reason="本地规则识别到明确动作",
                candidates=self._candidate_list(local_intents, model_route),
            )

        if model_route is not None:
            if self._looks_like_vague_office_action(message):
                return self._generic_intent_clarification(message, model_route, reason="办公动作不完整")
            if model_route.confidence < 0.45:
                return self._generic_intent_clarification(message, model_route, reason="意图置信度较低")
            candidate_intents = {candidate.intent for candidate in model_route.candidates}
            if len(candidate_intents - {"chat"}) > 1:
                return self._generic_intent_clarification(message, model_route, reason="存在多个可能工具")
            return model_route

        if self._is_bare_topic_message(message):
            return IntentRouteResult(
                intent=AgentIntent.CHAT.value,
                primary_tool="chat",
                confidence=0.95,
                reason="topic_discussion",
                candidates=[IntentCandidate(intent="chat", tool="chat", confidence=0.95, reason="topic_discussion")],
            )

        if self._looks_like_vague_office_action(message):
            return self._generic_intent_clarification(message, model_route, reason="办公动作不完整")

        return IntentRouteResult(
            intent=AgentIntent.CHAT.value,
            primary_tool="chat",
            confidence=0.8,
            reason="未发现明确产物动作，按普通回复处理",
            candidates=[IntentCandidate(intent="chat", tool="chat", confidence=0.8, reason="default")],
        )

    async def _classify_chat_intent_with_model(self, message: str) -> IntentRouteResult | None:
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
2. 不要因为出现“生成”就默认 docx；“生成思路图/脑图/流程图/架构图/导图/时序图/序列图”应选择 board。
3. 如果用户要演示文稿、幻灯片、PPT、路演或汇报材料，选择 ppt。
4. 只有用户明确要求“创建/生成/写成/起草/整理/导出/同步”文字产物时，才选择 docx。
5. 只有用户明确要求“创建/生成/制作/更新”PPT、幻灯片、演示文稿时，才选择 ppt。
6. 只有用户明确要求“创建/生成/绘制/制作”画板、白板、流程图、脑图、架构图、时序图、序列图等可视化产物时，才选择 board。
7. 用户只输入主题、标题、名词短语或想讨论一个方案/策略/问题时，选择 chat；不要替用户默认创建文档。
8. 如果需要修改已有产物，优先选择对应 edit 工具。

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
            return None
        return self._parse_model_route(result, message=message)

    def _parse_model_route(self, result: str, *, message: str = "") -> IntentRouteResult | None:
        normalized = result.strip().lower()
        if not normalized:
            return None

        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            parsed = None

        intent_value = normalized
        tool_value = ""
        confidence = 1.0
        reason = ""
        if isinstance(parsed, dict):
            raw_intent = parsed.get("intent")
            intent_value = raw_intent.strip().lower() if isinstance(raw_intent, str) else ""
            raw_tool = parsed.get("primary_tool") or parsed.get("tool")
            tool_value = raw_tool.strip().lower() if isinstance(raw_tool, str) else ""
            raw_confidence = parsed.get("confidence")
            if isinstance(raw_confidence, int | float):
                confidence = float(raw_confidence)
            raw_reason = parsed.get("reason")
            reason = raw_reason.strip() if isinstance(raw_reason, str) else ""

        tool_intent = self._intent_from_tool(tool_value)
        parsed_intent = tool_intent or self._intent_from_value(intent_value)
        if parsed_intent is None:
            return None
        if parsed_intent != AgentIntent.CHAT and self._looks_like_vague_office_action(message):
            return IntentRouteResult(
                intent=AgentIntent.CHAT.value,
                primary_tool="chat",
                confidence=min(confidence, 0.4),
                reason=reason or "用户动作缺少范围和格式",
                candidates=[
                    IntentCandidate(intent=parsed_intent.value, tool=tool_value or self._primary_tool_for_intent(parsed_intent), confidence=confidence, reason=reason),
                    IntentCandidate(intent="chat", tool="chat", confidence=0.45, reason="可直接讨论"),
                ],
            )
        if parsed_intent != AgentIntent.CHAT and not self._tool_intent_has_explicit_user_action(message, parsed_intent):
            return IntentRouteResult(
                intent=AgentIntent.CHAT.value,
                primary_tool="chat",
                confidence=min(confidence, 0.7),
                reason=reason or "模型选择了产物工具，但用户缺少明确动作",
                candidates=[
                    IntentCandidate(intent=parsed_intent.value, tool=tool_value or self._primary_tool_for_intent(parsed_intent), confidence=confidence, reason=reason),
                    IntentCandidate(intent="chat", tool="chat", confidence=0.75, reason="缺少明确生成/修改动作"),
                ],
            )
        return IntentRouteResult(
            intent=parsed_intent.value,
            primary_tool=tool_value or self._primary_tool_for_intent(parsed_intent),
            confidence=confidence,
            reason=reason or "模型路由",
            candidates=[IntentCandidate(intent=parsed_intent.value, tool=tool_value or self._primary_tool_for_intent(parsed_intent), confidence=confidence, reason=reason)],
        )

    def _parse_model_intent(self, result: str, *, message: str = "") -> AgentIntent | None:
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
            if not self._tool_intent_has_explicit_user_action(message, tool_intent):
                return AgentIntent.CHAT
            return tool_intent
        if intent_value == "board":
            if not self._tool_intent_has_explicit_user_action(message, AgentIntent.BOARD):
                return AgentIntent.CHAT
            return AgentIntent.BOARD
        if intent_value == "docx" or intent_value == "document":
            if not self._tool_intent_has_explicit_user_action(message, AgentIntent.DOCX):
                return AgentIntent.CHAT
            return AgentIntent.DOCX
        if intent_value == "ppt" or intent_value == "presentation":
            if not self._tool_intent_has_explicit_user_action(message, AgentIntent.PPT):
                return AgentIntent.CHAT
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

    def _intent_from_value(self, value: str) -> AgentIntent | None:
        if value in {"chat"}:
            return AgentIntent.CHAT
        if value in {"docx", "document"}:
            return AgentIntent.DOCX
        if value in {"ppt", "presentation"}:
            return AgentIntent.PPT
        if value in {"board"}:
            return AgentIntent.BOARD
        return None

    def _local_explicit_intents(self, message: str) -> list[AgentIntent]:
        intents: list[AgentIntent] = []
        for intent in (AgentIntent.BOARD, AgentIntent.PPT, AgentIntent.DOCX):
            if self._tool_intent_has_explicit_user_action(message, intent):
                intents.append(intent)
        return intents

    def _candidate_list(
        self,
        local_intents: list[AgentIntent],
        model_route: IntentRouteResult | None,
    ) -> list[IntentCandidate]:
        candidates: list[IntentCandidate] = []
        for intent in local_intents:
            candidates.append(IntentCandidate(intent=intent.value, tool=self._primary_tool_for_intent(intent), confidence=0.95, reason="local_rule"))
        if model_route is not None:
            candidates.extend(model_route.candidates)
        if not candidates:
            candidates.append(IntentCandidate(intent="chat", tool="chat", confidence=0.8, reason="default"))
        deduped: dict[str, IntentCandidate] = {}
        for candidate in candidates:
            key = f"{candidate.intent}:{candidate.tool or ''}"
            if key not in deduped or candidate.confidence > deduped[key].confidence:
                deduped[key] = candidate
        return list(deduped.values())

    def _primary_tool_for_intent(
        self,
        intent: AgentIntent,
        *,
        current_artifact: AgentChatArtifact | None = None,
        message: str = "",
    ) -> str:
        if current_artifact is not None and self._is_current_artifact_ambiguous(message, current_artifact):
            edit_tool = self._edit_tool_for_artifact(current_artifact)
            if edit_tool:
                return edit_tool
        if intent == AgentIntent.DOCX:
            return "docx"
        if intent == AgentIntent.PPT:
            return "ppt"
        if intent == AgentIntent.BOARD:
            return "board"
        return "chat"

    def _edit_tool_for_artifact(self, artifact: AgentChatArtifact | None) -> str | None:
        if artifact is None:
            return None
        if artifact.kind == "docx":
            return "docx_edit"
        if artifact.kind == "ppt":
            return "ppt_edit"
        if artifact.kind == "board":
            return "board_edit"
        return None

    def _artifact_label(self, artifact: AgentChatArtifact | None) -> str:
        if artifact is None:
            return "产物"
        if artifact.kind == "docx":
            return "文档"
        if artifact.kind == "ppt":
            return "PPT"
        if artifact.kind == "board":
            return "画板"
        return "产物"

    def _is_current_artifact_ambiguous(self, message: str, artifact: AgentChatArtifact | None) -> bool:
        if artifact is None:
            return False
        if not message.strip():
            return False
        normalized = message.lower()
        vague_actions = ("整理一下", "优化一下", "改一下", "处理一下", "完善一下", "帮我整理", "帮我优化", "帮我改", "帮我处理")
        if any(keyword in message or keyword in normalized for keyword in vague_actions):
            return not any(keyword in message or keyword in normalized for keyword in ("新建", "生成一份", "生成一个", "ppt", "文档", "画板", "流程图"))
        return False

    def _clarification_route(
        self,
        message: str,
        *,
        question: str,
        options: list[IntentClarificationOption],
        reason: str,
        candidates: list[IntentCandidate],
    ) -> IntentRouteResult:
        return IntentRouteResult(
            intent="chat",
            primary_tool="chat",
            confidence=0.0,
            reason=reason,
            candidates=candidates,
            needs_clarification=True,
            clarification_question=question,
            clarification_options=options,
            pending_route={"original_message": message, "reason": reason},
        )

    def _generic_intent_clarification(
        self,
        message: str,
        model_route: IntentRouteResult | None,
        *,
        reason: str,
    ) -> IntentRouteResult:
        return self._clarification_route(
            message,
            question="你是想直接讨论这个主题，还是生成一份文档、PPT 或画板？",
            options=[
                IntentClarificationOption(label="直接讨论", intent="chat", tool="chat", description="只做普通回复，不创建产物。"),
                IntentClarificationOption(label="生成文档", intent="docx", tool="docx", description="输出 Markdown 文档并可同步飞书。"),
                IntentClarificationOption(label="生成 PPT", intent="ppt", tool="ppt", description="创建 AI PPT 后台任务。"),
                IntentClarificationOption(label="生成画板", intent="board", tool="board", description="创建飞书画板或图示。"),
            ],
            reason=reason,
            candidates=self._candidate_list([], model_route),
        )

    def _tool_intent_has_explicit_user_action(self, message: str, intent: AgentIntent) -> bool:
        if intent == AgentIntent.CHAT:
            return True
        normalized = message.lower()
        action_pattern = (
            r"(请|帮我|帮忙|需要|我要|想要|生成|创建|新建|制作|做一份|做个|写|写成|起草|整理|整理成|输出|导出|同步|更新|修改|改|画|绘制|来一份|"
            r"generate|create|make|draw|update|edit)"
        )
        if not re.search(action_pattern, message):
            return False
        if intent == AgentIntent.DOCX:
            return bool(
                re.search(r"(文档|报告|纪要|文章|文案|草稿|提纲|大纲|总结|说明|介绍|方案|策略|材料|一份|一篇|一段|docx?|document|report)", normalized)
            )
        if intent == AgentIntent.PPT:
            return bool(re.search(r"(ppt|演示|幻灯片|路演|汇报材料|展示材料|presentation|slides?)", normalized))
        if intent == AgentIntent.BOARD:
            return bool(
                re.search(
                    r"(画板|白板|流程图|架构图|思维导图|思路图|脑图|导图|泳道图|时序图|序列图|饼图|柱状图|折线图|面积图|line\s*chart|bar\s*chart|pie\s*chart|sequence\s*diagram|board)",
                    normalized,
                )
            )
        return False

    def _is_bare_topic_message(self, message: str) -> bool:
        normalized = message.strip()
        if not normalized:
            return False
        if len(normalized) > 80:
            return False
        if re.search(r"[?？]", normalized):
            return False
        if re.search(
            r"(怎么|如何|为什么|是否|吗|么|多少|哪|谁|何时|何地|what|why|how|when|where|who)",
            normalized,
            flags=re.I,
        ):
            return False
        if re.search(
            r"(请|帮我|帮忙|需要|我要|想要|生成|创建|新建|制作|做一份|做个|写|写成|起草|整理|整理成|输出|导出|同步|更新|修改|改|画|绘制|来一份|"
            r"generate|create|make|draw|update|edit)",
            normalized,
            flags=re.I,
        ):
            return False
        compact = re.sub(r"\s+", "", normalized)
        if len(compact) < 2:
            return False
        return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", compact))

    def _looks_like_vague_office_action(self, message: str) -> bool:
        compact = re.sub(r"[\s，。！？!?、,.；;：:（）()【】\[\]「」『』\"'“”‘’]+", "", message).lower()
        if not compact:
            return False
        for suffix in ("吧", "呗", "哈", "呀", "啊", "呢", "啦", "哦"):
            while compact.endswith(suffix):
                compact = compact[: -len(suffix)]
        vague_requests = {
            "整理",
            "整理下",
            "整理一下",
            "处理",
            "处理下",
            "处理一下",
            "帮我整理",
            "帮我整理下",
            "帮我整理一下",
            "帮我处理",
            "帮我处理下",
            "帮我处理一下",
            "麻烦整理",
            "麻烦整理下",
            "麻烦整理一下",
            "麻烦处理",
            "麻烦处理下",
            "麻烦处理一下",
            "请整理",
            "请整理下",
            "请整理一下",
            "请处理",
            "请处理下",
            "请处理一下",
        }
        return compact in vague_requests


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
        bitable_service: BitableService | None = None,
    ) -> None:
        self._router = RouterAgent(llm_client)
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
        self._bitable_service = bitable_service
        self._context_assembler = AgentContextAssembler()
        self._runtime = AgentRuntime(
            retriever=AgentRAGRetriever(rag_service=rag_service, bitable_service=bitable_service),
            tool_handlers={
                "docx": self._runtime_docx_tool,
                "ppt": self._runtime_ppt_tool,
                "board": self._runtime_board_tool,
                "bitable_schema": self._runtime_bitable_schema_tool,
                "bitable_search": self._runtime_bitable_search_tool,
                "bitable_archive": self._runtime_bitable_archive_tool,
            },
        )

    def _extract_ppt_page_count(self, message: str) -> int:
        match = re.search(r"(\d{1,2})\s*(?:页|p|P|slides?|张)", message)
        if not match:
            return 6
        return max(1, min(20, int(match.group(1))))

    def _resolve_ppt_design_mode(self, *, requested: object = None, message: str = "") -> str:
        normalized = str(requested or "").strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"free", "freeform", "free_design", "creative_freeform", "ppt_master_free_design"}:
            return "free_design"
        if normalized in {"template", "templated", "renderer", "ppt_master_template"}:
            return "template"

        message_lower = message.lower()
        if any(keyword in message or keyword in message_lower for keyword in _PPT_FREE_DESIGN_KEYWORDS):
            return "free_design"
        if any(keyword in message or keyword in message_lower for keyword in _PPT_TEMPLATE_KEYWORDS):
            return "template"
        return "template"

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
            if (
                hasattr(self._sync_service, "update_session_route_state")
                and not self._is_pending_clarification_request(request)
                and not self._response_is_clarification_request(response)
            ):
                await self._sync_service.update_session_route_state(response.session_id, None)
            await self._echo_feishu_chat_reply_if_needed(request, response, artifact=artifact)
            return

        await self._sync_service.publish_error(response.session_id, response.message, response.error)

    async def _resolve_pending_route_reply(self, request: AgentChatRequest) -> AgentChatRequest:
        if request.forced_intent is not None:
            return request
        if self._sync_service is None or not hasattr(self._sync_service, "get_session"):
            return request
        try:
            session = await self._sync_service.get_session(request.session_id)
        except Exception:  # noqa: BLE001
            return request
        route_state = getattr(session, "route_state", None)
        if self._is_waiting_clarification_route(route_state):
            selected_intent = self._intent_from_clarification_reply(request.message)
            if selected_intent is None:
                return request.model_copy(update={"forced_intent": "chat", "sender": {**(request.sender or {}), "pending_clarification": True}})
            original = str(route_state.get("original_message") or "").strip()
            if hasattr(self._sync_service, "update_session_route_state"):
                await self._sync_service.update_session_route_state(request.session_id, None)
            return request.model_copy(
                update={
                    "message": original or request.message,
                    "forced_intent": selected_intent.value,
                }
            )

        messages = getattr(session, "messages", None)
        if not isinstance(messages, list) or len(messages) < 2:
            return request

        def _payload(message: Any) -> dict[str, Any]:
            if isinstance(message, dict):
                return message
            if hasattr(message, "model_dump"):
                dumped = message.model_dump()
                return dumped if isinstance(dumped, dict) else {}
            return {
                "role": getattr(message, "role", None),
                "content": getattr(message, "content", None),
            }

        normalized = [_payload(message) for message in messages]
        last = normalized[-1]
        last_role = str(last.get("role") or "").lower()
        last_content = str(last.get("content") or "")
        if last_role not in {"assistant", "eko", "bot", "system"}:
            return request
        if "确认" not in last_content and "直接讨论" not in last_content and "修改当前" not in last_content:
            return request

        original = next(
            (
                str(message.get("content") or "").strip()
                for message in reversed(normalized[:-1])
                if str(message.get("role") or "").lower() == "user" and str(message.get("content") or "").strip()
            ),
            "",
        )
        if not original:
            return request

        selected_intent = self._intent_from_clarification_reply(request.message)
        if selected_intent is None:
            return request.model_copy(update={"forced_intent": "chat", "sender": {**(request.sender or {}), "pending_clarification": True}})
        return request.model_copy(
            update={
                "message": original,
                "forced_intent": selected_intent.value,
            }
        )

    def _is_waiting_clarification_route(self, route_state: Any) -> bool:
        return isinstance(route_state, dict) and route_state.get("state") == "awaiting_clarification"

    def _is_pending_clarification_request(self, request: AgentChatRequest) -> bool:
        return bool(request.sender and request.sender.get("pending_clarification") is True)

    def _response_is_clarification_request(self, response: AgentChatResponse) -> bool:
        return any(getattr(event, "event", None) == "clarification.requested" for event in (response.events or []))

    def _intent_from_clarification_reply(self, message: str) -> AgentIntent | None:
        normalized = message.strip().lower()
        if not normalized:
            return None
        if any(keyword in message or keyword in normalized for keyword in ("直接讨论", "普通回复", "直接回复", "chat")):
            return AgentIntent.CHAT
        if any(keyword in message or keyword in normalized for keyword in ("生成文档", "新建文档", "文档", "docx", "document")):
            return AgentIntent.DOCX
        if any(keyword in message or keyword in normalized for keyword in ("修改当前ppt", "生成 ppt", "生成PPT", "新建 ppt", "ppt", "slides", "presentation")):
            return AgentIntent.PPT
        if any(keyword in message or keyword in normalized for keyword in ("修改当前画板", "生成画板", "新建画板", "画板", "board", "流程图", "时序图")):
            return AgentIntent.BOARD
        return None

    async def _pending_clarification_response(self, request: AgentChatRequest) -> AgentChatResponse | None:
        if not request.sender or request.sender.get("pending_clarification") is not True:
            return None
        if self._sync_service is None or not hasattr(self._sync_service, "get_session"):
            return None
        try:
            session = await self._sync_service.get_session(request.session_id)
        except Exception:  # noqa: BLE001
            return None
        route_state = getattr(session, "route_state", None)
        if self._is_waiting_clarification_route(route_state):
            response = await self._response_for_structured_clarification_reply(request.session_id, request.message, route_state)
            if response is not None:
                return AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.CHAT.value,
                    status="completed",
                    message=response,
                )

        messages = getattr(session, "messages", None)
        if not isinstance(messages, list):
            return None

        for message in reversed(messages):
            payload = message.model_dump() if hasattr(message, "model_dump") else message
            if not isinstance(payload, dict):
                continue
            role = str(payload.get("role") or "").lower()
            content = str(payload.get("content") or "").strip()
            if role in {"assistant", "eko", "bot", "system"} and content:
                return AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.CHAT.value,
                    status="completed",
                    message=content,
                )
        return None

    async def _response_for_structured_clarification_reply(self, session_id: str, message: str, route_state: dict[str, Any]) -> str | None:
        if route_state.get("clarification_type") != "organize_request":
            return None
        slots = route_state.get("slots")
        current_slots = slots if isinstance(slots, dict) else {}
        parsed_slots = self._parse_organize_clarification_slots(message)
        merged_slots = {**current_slots, **parsed_slots}
        next_state = dict(route_state)
        next_state["slots"] = merged_slots
        if hasattr(self._sync_service, "update_session_route_state"):
            await self._sync_service.update_session_route_state(session_id, next_state)
        required_slots = route_state.get("required_slots")
        required = required_slots if isinstance(required_slots, list) else []
        missing_slots = [slot for slot in required if slot not in merged_slots]
        if missing_slots == ["output_format"]:
            return self._organize_format_followup_message(route_state)
        if missing_slots:
            return None
        return None

    def _organize_format_followup_message(self, route_state: dict[str, Any]) -> str:
        options = route_state.get("options") if isinstance(route_state.get("options"), dict) else {}
        raw_formats = options.get("output_format") if isinstance(options, dict) else None
        formats = raw_formats if isinstance(raw_formats, list) else ["summary", "bullet_list", "minutes", "document"]
        labels = {
            "summary": "摘要",
            "bullet_list": "要点列表",
            "minutes": "会议纪要",
            "document": "文档",
        }
        readable_formats = [labels.get(str(item), str(item)) for item in formats]
        return f"好的，我会整理你指定的内容。你希望整理成什么形式？比如{'、'.join(readable_formats)}？"

    def _parse_organize_clarification_slots(self, message: str) -> dict[str, str]:
        compact = re.sub(r"\s+", "", message)
        slots: dict[str, str] = {}
        if any(keyword in compact for keyword in ("对话记录", "聊天记录", "刚才的对话", "刚才聊天", "群聊上下文", "上下文")):
            slots["content_scope"] = "recent_chat"
        if any(keyword in compact for keyword in ("摘要", "总结")):
            slots["output_format"] = "summary"
        elif any(keyword in compact for keyword in ("要点", "列表")):
            slots["output_format"] = "bullet_list"
        elif "会议纪要" in compact:
            slots["output_format"] = "minutes"
        elif any(keyword in compact for keyword in ("文档", "报告", "markdown")):
            slots["output_format"] = "document"
        return slots

    async def _echo_feishu_chat_reply_if_needed(
        self,
        request: AgentChatRequest,
        response: AgentChatResponse,
        *,
        artifact: dict[str, Any] | None,
    ) -> None:
        if response.status != "completed" or response.intent != AgentIntent.CHAT.value:
            return
        if not response.message.strip():
            return
        if self._sync_service is None or not hasattr(self._sync_service, "get_session"):
            return
        session = await self._sync_service.get_session(request.session_id)
        if session is None:
            return
        if request.sender and request.sender.get("pending_clarification") is True:
            logger.info("Skip Feishu chat echo because session is waiting for clarification selection session=%s", request.session_id)
            return
        if getattr(session, "source", None) != "feishu":
            return
        if self._should_suppress_feishu_chat_echo(request, session):
            logger.info("Suppress Feishu chat echo for board-like/session-selection request session=%s", request.session_id)
            return
        if getattr(session, "reply_echo_sent", False):
            return
        if bool((artifact or {}).get("feishu_chat_reply_echo_sent")):
            return
        session_artifact = getattr(session, "artifact", None)
        if isinstance(session_artifact, dict) and session_artifact.get("feishu_chat_reply_echo_sent") is True:
            return
        chat_id = getattr(session, "chat_id", None) or self._extract_feishu_chat_id(request.session_id)
        if not isinstance(chat_id, str) or not chat_id:
            return
        if not await self._feishu_session_was_app_mention(request.session_id, chat_id):
            logger.info("Skip Feishu chat echo because source message did not mention app session=%s", request.session_id)
            return
        try:
            await self._feishu.send_text_message_to_chat(chat_id, response.message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Echo final chat reply to Feishu failed session=%s: %s", request.session_id, exc)
            return
        if hasattr(self._sync_service, "update_session_reply_echo_state"):
            await self._sync_service.update_session_reply_echo_state(request.session_id, sent=True)

    def _should_suppress_feishu_chat_echo(self, request: AgentChatRequest, session: Any) -> bool:
        session_intent = str(getattr(session, "intent", "") or "").strip().lower()
        if request.forced_intent == "board" or session_intent == AgentIntent.BOARD.value:
            return True
        return self._router._tool_intent_has_explicit_user_action(request.message, AgentIntent.BOARD)

    async def _prepare_agent_turn(
        self,
        request: AgentChatRequest,
        intent: AgentIntent,
        session_artifact: AgentChatArtifact | None,
        *,
        route_result: IntentRouteResult | None = None,
        execute_tools: bool = False,
    ):
        return await self._runtime.prepare_turn(
            request,
            routed_intent=intent,
            current_artifact=session_artifact,
            route_result=route_result,
            execute_tools=execute_tools,
        )

    def _runtime_tool_result(self, runtime_turn: Any, tool_name: str) -> dict[str, Any] | None:
        for item in getattr(runtime_turn, "tool_results", []):
            if item.get("tool") == tool_name and isinstance(item.get("result"), dict):
                return item["result"]
        return None

    def _events_from_traces(self, trace_events: list[Any]) -> list[Any]:
        return AgentEventProtocol.from_traces(trace_events)

    def _clarification_response_from_turn(
        self,
        request: AgentChatRequest,
        runtime_turn: Any,
    ) -> AgentChatResponse | None:
        if not getattr(runtime_turn, "clarification_requested", False):
            return None
        route = getattr(runtime_turn, "route_result", None)
        question = getattr(route, "clarification_question", None) or "请确认你希望我执行哪种动作。"
        return AgentChatResponse(
            session_id=request.session_id,
            intent=AgentIntent.CHAT.value,
            status="completed",
            message=question,
            events=self._events_from_traces(getattr(runtime_turn, "trace_events", [])),
        )

    async def _persist_runtime_clarification_route(
        self,
        request: AgentChatRequest,
        runtime_turn: Any,
    ) -> None:
        if self._sync_service is None or not hasattr(self._sync_service, "update_session_route_state"):
            return
        if not getattr(runtime_turn, "clarification_requested", False):
            return
        route = getattr(runtime_turn, "route_result", None)
        if route is None:
            return
        pending_route = getattr(route, "pending_route", None)
        original_message = request.message
        if isinstance(pending_route, dict):
            original_message = str(pending_route.get("original_message") or request.message)
        route_state = {
            "state": "awaiting_clarification",
            "clarification_type": "intent_route",
            "original_message": original_message,
            "reason": getattr(route, "reason", "") or "",
            "intent": getattr(route, "intent", "chat") or "chat",
            "primary_tool": getattr(route, "primary_tool", "chat") or "chat",
            "confidence": getattr(route, "confidence", 0.0) or 0.0,
            "candidates": [
                candidate.model_dump() if hasattr(candidate, "model_dump") else dict(candidate)
                for candidate in (getattr(route, "candidates", None) or [])
            ],
            "options": [
                option.model_dump() if hasattr(option, "model_dump") else dict(option)
                for option in (getattr(route, "clarification_options", None) or [])
            ],
        }
        await self._sync_service.update_session_route_state(request.session_id, route_state)

    async def _runtime_docx_tool(
        self,
        instruction: str,
        session_id: str | None = None,
        chat_history: list[dict[str, Any]] | None = None,
        retrieved_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        knowledge_docs = self._knowledge_docs_from_retrieved_context(retrieved_context)
        bitable_records = self._bitable_records_from_retrieved_context(retrieved_context)
        context = AgentContext(
            chat_history=[
                ChatMessage(
                    role=str(message.get("role") or ""),
                    content=str(message.get("content") or ""),
                )
                for message in (chat_history or [])
                if str(message.get("role") or "").strip() and str(message.get("content") or "").strip()
            ],
            knowledge_docs=knowledge_docs,
            bitable_records=bitable_records,
        )
        request = AgentChatRequest(
            session_id=session_id or "runtime",
            message=instruction,
            context=context if context.chat_history or context.knowledge_docs else None,
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
        resolved_design_mode = self._resolve_ppt_design_mode(requested=design_mode, message=instruction)
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
        chat_history: list[dict[str, Any]] | None = None,
        retrieved_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        knowledge_docs = self._knowledge_docs_from_retrieved_context(retrieved_context)
        bitable_records = self._bitable_records_from_retrieved_context(retrieved_context)
        context = AgentContext(
            chat_history=[
                ChatMessage(
                    role=str(message.get("role") or ""),
                    content=str(message.get("content") or ""),
                )
                for message in (chat_history or [])
                if str(message.get("role") or "").strip() and str(message.get("content") or "").strip()
            ],
            knowledge_docs=knowledge_docs,
            bitable_records=bitable_records,
        )
        grounded_instruction = self._build_board_instruction_with_context(instruction, context)
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

    def _build_board_instruction_with_context(self, instruction: str, context: AgentContext) -> str:
        sections = ["## 用户需求", instruction]
        if context.chat_history:
            sections.extend(
                [
                    "",
                    "## 飞书群聊上下文",
                    *[f"{message.role}: {message.content}" for message in context.chat_history],
                ]
            )
        if context.knowledge_docs:
            sections.extend(["", *self._format_agent_knowledge_docs(context.knowledge_docs)])
        if context.bitable_records:
            sections.extend(["", *self._format_agent_bitable_records(context.bitable_records)])
        return "\n".join(sections)

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

    def _bitable_records_from_retrieved_context(
        self,
        retrieved_context: list[dict[str, Any]] | None,
    ) -> list[BitableRecord]:
        records: list[BitableRecord] = []
        for item in retrieved_context or []:
            if str(item.get("source_type") or "") != "bitable":
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            fields = metadata.get("fields") if isinstance(metadata.get("fields"), dict) else {}
            if not fields:
                fields = {"内容": str(item.get("content") or "")}
            records.append(
                BitableRecord(
                    table_name=str(metadata.get("table_name") or metadata.get("source_name") or "") or None,
                    fields={str(key): value for key, value in fields.items()},
                )
            )
        return records

    def _format_agent_bitable_records(self, records: list[BitableRecord]) -> list[str]:
        if not records:
            return []
        lines = ["## Bitable 结构化数据"]
        for record in records:
            if record.table_name:
                lines.append(f"### {record.table_name}")
            for key, value in list(record.fields.items())[:20]:
                lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append("## Bitable 使用要求")
        lines.append("生成内容可以引用以上结构化记录；如果 Bitable 数据为空或不足，继续使用聊天上下文和 RAG。")
        return lines

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

    def _append_bitable_context_to_instruction(self, instruction: str, records: list[BitableRecord]) -> str:
        context_lines = self._format_agent_bitable_records(records)
        if not context_lines:
            return instruction
        return "\n".join([instruction, "", *context_lines])

    def _request_with_retrieved_context(
        self,
        request: AgentChatRequest,
        retrieved_context: list[Any],
    ) -> AgentChatRequest:
        dumped_context = [
            item.model_dump() if hasattr(item, "model_dump") else dict(item)
            for item in retrieved_context
        ]
        docs = self._knowledge_docs_from_retrieved_context(dumped_context)
        bitable_records = self._bitable_records_from_retrieved_context(dumped_context)
        if not docs and not bitable_records:
            return request
        context = request.context or AgentContext()
        merged = context.model_copy(
            update={
                "knowledge_docs": [*context.knowledge_docs, *docs],
                "bitable_records": [*context.bitable_records, *bitable_records],
            }
        )
        return request.model_copy(update={"context": merged})

    async def _runtime_bitable_schema_tool(
        self,
        workspace_id: str = "Feishu_demo_Eko",
        created_by: str | None = None,
    ) -> dict[str, Any]:
        if self._bitable_service is None:
            return {"sources": []}
        return {
            "sources": [
                source.model_dump()
                for source in await self._bitable_service.list_sources(workspace_id, created_by=created_by)
            ]
            if created_by
            else []
        }

    async def _runtime_bitable_search_tool(
        self,
        query: str,
        workspace_id: str = "Feishu_demo_Eko",
        limit: int = 8,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        if self._bitable_service is None:
            return {"records": [], "failures": []}
        return (
            await self._bitable_service.query_records(
                BitableQueryRequest(workspace_id=workspace_id, query=query, limit=limit),
                created_by=created_by,
            )
        ).model_dump()

    async def _runtime_bitable_archive_tool(
        self,
        session_id: str,
        artifact: dict[str, Any],
        workspace_id: str = "Feishu_demo_Eko",
        created_by: str | None = None,
    ) -> dict[str, Any]:
        if self._bitable_service is None:
            return {"results": []}
        return (
            await self._bitable_service.archive_artifact(
                BitableArchiveRequest(workspace_id=workspace_id, session_id=session_id, artifact=artifact),
                created_by=created_by,
            )
        ).model_dump()

    def _build_chat_prompt(
        self,
        request: AgentChatRequest,
        retrieved_context: list[Any] | None = None,
        route_result: IntentRouteResult | None = None,
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
        if enriched_request.context and enriched_request.context.bitable_records:
            sections.extend(self._format_agent_bitable_records(enriched_request.context.bitable_records))
            sections.append("")
        if route_result is not None and route_result.reason == "topic_discussion":
            sections.extend(
                [
                    "## 回复要求",
                    "用户只给了一个主题或议题。请直接围绕这个主题给出简洁、有结构的讨论起点：先说明你对主题的理解，再给 3-5 个可展开的方向或关键问题。不要询问是否生成文档、PPT 或画板，不要承诺创建任何产物。",
                    "",
                ]
            )
        sections.extend(["## 当前问题", enriched_request.message])
        return "\n".join(sections)

    def _clean_chat_reply(self, reply: str) -> str:
        lines = reply.splitlines()
        noisy_prefixes = (
            "收到。我先理解你的任务",
            "我判断这次要走",
            "开始检索相关知识",
            "已检索到",
            "规划完成",
            "直接回答用户问题",
        )
        noisy_exact = {"1. 生成回复", "好的，我现在直接回复这个问题。"}
        cleaned: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped and not cleaned:
                continue
            if stripped in noisy_exact:
                continue
            if any(stripped.startswith(prefix) for prefix in noisy_prefixes):
                continue
            cleaned.append(line)
        while cleaned and not cleaned[0].strip():
            cleaned.pop(0)
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        return "\n".join(cleaned).strip() or reply.strip()

    async def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        """Handle direct agent chat requests with intent-based routing."""
        intent = AgentIntent.CHAT
        trace_events = []
        try:
            request = await self._resolve_pending_route_reply(request)
            pending_clarification_response = await self._pending_clarification_response(request)
            if pending_clarification_response is not None:
                await self._publish_chat_result(request, pending_clarification_response)
                return pending_clarification_response
            request = await self._context_assembler.assemble(request, sync_service=self._sync_service)
            session_artifact = await self._get_session_artifact(request)
            editable_document = await self._get_editable_document(request)
            route_result: IntentRouteResult | None = None
            intent = self._forced_or_classified_intent(request)
            if intent == AgentIntent.UNKNOWN:
                route_result = await self._router.route_chat_intent(
                    request.message,
                    current_artifact=session_artifact,
                    forced_intent=request.forced_intent,
                )
                intent = AgentIntent(route_result.intent)
            else:
                route_result = await self._router.route_chat_intent(
                    request.message,
                    current_artifact=session_artifact,
                    forced_intent=intent.value,
                )
            current_artifact_operation = self._resolve_current_artifact_operation(session_artifact, request, intent)
            if current_artifact_operation == "docx":
                editable_document = session_artifact if session_artifact and session_artifact.kind == "docx" else editable_document
            current_ppt_update = current_artifact_operation == "ppt" or self._should_continue_current_ppt(session_artifact, request, intent)
            if current_ppt_update:
                intent = AgentIntent.PPT
            if current_artifact_operation == "board":
                intent = AgentIntent.BOARD

            should_execute_runtime_tools = (
                intent == AgentIntent.PPT and not current_ppt_update
                and current_artifact_operation != "docx"
                and not self._should_edit_current_document(editable_document, request, intent)
            )
            runtime_turn = await self._prepare_agent_turn(
                request,
                intent,
                session_artifact,
                route_result=route_result,
                execute_tools=should_execute_runtime_tools,
            )
            trace_events = runtime_turn.trace_events
            clarification_response = self._clarification_response_from_turn(request, runtime_turn)
            if clarification_response is not None:
                await self._persist_runtime_clarification_route(request, runtime_turn)
                await self._publish_chat_result(request, clarification_response)
                return clarification_response
            docx_tool_result = self._runtime_tool_result(runtime_turn, "docx")
            ppt_tool_result = self._runtime_tool_result(runtime_turn, "ppt")
            board_tool_result = self._runtime_tool_result(runtime_turn, "board")
            events_v1 = AgentEventProtocol.from_traces(trace_events)
            enriched_request = self._request_with_retrieved_context(request, runtime_turn.retrieved_context)

            if current_artifact_operation == "docx" and editable_document is not None:
                response = await self._edit_current_document(request, editable_document)
                response.events = self._events_from_traces(trace_events)
                await self._publish_chat_result(request, response)
                return response
            if self._should_edit_current_document(editable_document, request, intent):
                response = await self._edit_current_document(request, editable_document)
                response.events = self._events_from_traces(trace_events)
                await self._publish_chat_result(request, response)
                return response

            events_v1 = self._events_from_traces(trace_events)

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
                    events=events_v1,
                )
                synced_url = await self._sync_document_to_feishu_chat(request, content)
                if synced_url and response.artifact is not None:
                    response.message = "文档生成完成，并已同步到飞书。"
                    response.artifact.sharing_url = synced_url
                archive_results = await self._archive_artifact_to_bitable(request, response, trace_events)
                if archive_results and response.artifact is not None:
                    response.artifact = response.artifact.model_copy(update={"bitable_archive_results": archive_results})
                response.events = self._events_from_traces(trace_events)
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
                    job = self._aippt_service.create_job_from_request(
                        PPTGenerationRequest(
                            topic=self._build_ppt_topic(enriched_request, session_artifact=None),
                            page_count=self._resolve_ppt_page_count(enriched_request, session_artifact=None),
                            style="clean_business",
                            design_mode=self._resolve_ppt_design_mode(message=enriched_request.message),
                        )
                    )
                    artifact = self._ppt_artifact_from_job(job)
                    job_id = job.job_id

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
                    board_instruction = self._build_board_instruction_with_context(
                        request.message,
                        enriched_request.context or AgentContext(),
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
                    events=events_v1,
                    error=completed_task.error_message if is_failed else None,
                )
                if created_board_document is not None and not is_failed:
                    await self._share_board_result_to_feishu_chat(request, created_board_document, completed_task)
                archive_results = await self._archive_artifact_to_bitable(request, response, trace_events)
                if archive_results and response.artifact is not None:
                    response.artifact = response.artifact.model_copy(update={"bitable_archive_results": archive_results})
                response.events = self._events_from_traces(trace_events)
                await self._publish_chat_result(request, response)
                return response

            chat_prompt = self._build_chat_prompt(request, runtime_turn.retrieved_context, route_result=route_result)

            reply = await self._llm.generate(
                "你是 Eko 智能办公助手。请直接、友好地回答用户问题。若 RAG 知识库资料与问题相关，必须优先依据知识库资料回答；不要编造知识库未提供的信息。",
                chat_prompt,
            )
            reply = self._clean_chat_reply(reply)
            response = AgentChatResponse(
                session_id=request.session_id,
                intent=AgentIntent.CHAT.value,
                status="completed",
                message=reply,
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
                events=AgentEventProtocol.from_traces(trace_events),
                error=str(exc),
            )
            await self._publish_chat_result(request, response)
            return response

    async def chat_stream_events(self, request: AgentChatRequest) -> AsyncIterator[dict[str, Any]]:
        """Stream visible agent reasoning/planning/tool progress for chat requests."""
        intent = AgentIntent.CHAT
        trace_events = []
        yield AgentEventProtocol.start(request.planning_enabled)

        try:
            request = await self._resolve_pending_route_reply(request)
            pending_clarification_response = await self._pending_clarification_response(request)
            if pending_clarification_response is not None:
                await self._publish_chat_result(request, pending_clarification_response)
                yield AgentEventProtocol.result(pending_clarification_response, pending_clarification_response.message)
                return
            request = await self._context_assembler.assemble(request, sync_service=self._sync_service)
            session_artifact = await self._get_session_artifact(request)
            editable_document = await self._get_editable_document(request)
            route_result: IntentRouteResult | None = None
            intent = self._forced_or_classified_intent(request)
            if intent == AgentIntent.UNKNOWN:
                route_result = await self._router.route_chat_intent(
                    request.message,
                    current_artifact=session_artifact,
                    forced_intent=request.forced_intent,
                )
                intent = AgentIntent(route_result.intent)
            else:
                route_result = await self._router.route_chat_intent(
                    request.message,
                    current_artifact=session_artifact,
                    forced_intent=intent.value,
                )
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
                yield AgentEventProtocol.tool_started(intent.value, "docx_edit", "正在处理。")
                response = await self._edit_current_document(request, editable_document)
                await self._publish_chat_result(request, response)
                yield AgentEventProtocol.result(response, response.message)
                return

            if current_ppt_update or current_artifact_operation == "board":
                artifact_kind = "ppt" if current_ppt_update else "board"
                yield AgentEventProtocol.tool_started(
                    intent.value,
                    "ppt_edit" if artifact_kind == "ppt" else "board_edit",
                    "正在处理。",
                )
                execution_request = request.model_copy(update={"planning_enabled": False})
                response = await self.chat(execution_request)
                yield AgentEventProtocol.result(response, response.message)
                return

            runtime_turn = await self._prepare_agent_turn(
                request,
                intent,
                session_artifact,
                route_result=route_result,
                execute_tools=intent == AgentIntent.PPT and not current_ppt_update,
            )
            trace_events = runtime_turn.trace_events
            for trace_event in trace_events:
                if trace_event.type in {"clarification_requested"}:
                    yield AgentEventProtocol.from_trace(trace_event).model_dump()
            clarification_response = self._clarification_response_from_turn(request, runtime_turn)
            if clarification_response is not None:
                await self._persist_runtime_clarification_route(request, runtime_turn)
                await self._publish_chat_result(request, clarification_response)
                yield AgentEventProtocol.result(clarification_response, clarification_response.message)
                return
            docx_tool_result = self._runtime_tool_result(runtime_turn, "docx")
            ppt_tool_result = self._runtime_tool_result(runtime_turn, "ppt")
            board_tool_result = self._runtime_tool_result(runtime_turn, "board")

            yield AgentEventProtocol.tool_started(intent.value, intent.value, "正在处理。")

            if intent == AgentIntent.DOCX and docx_tool_result is not None and docx_tool_result.get("content") is not None:
                content = str(docx_tool_result["content"])
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.DOCX.value,
                    status="completed",
                    message="文档生成完成。",
                    artifact=AgentChatArtifact(kind="docx", content=content),
                    events=self._events_from_traces(trace_events),
                )
                synced_url = await self._sync_document_to_feishu_chat(request, content)
                if synced_url and response.artifact is not None:
                    response.message = "文档生成完成，并已同步到飞书。"
                    response.artifact.sharing_url = synced_url
                archive_results = await self._archive_artifact_to_bitable(request, response, trace_events)
                if archive_results and response.artifact is not None:
                    response.artifact = response.artifact.model_copy(update={"bitable_archive_results": archive_results})
                response.events = self._events_from_traces(trace_events)
                await self._publish_chat_result(request, response)
            elif intent == AgentIntent.PPT and ppt_tool_result is not None:
                artifact = self._ppt_artifact_from_tool_result(ppt_tool_result)
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.PPT.value,
                    status="completed",
                    message="AI PPT 任务已创建，正在后台生成。",
                    artifact=artifact,
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
                    events=self._events_from_traces(trace_events),
                    error=completed_task.error_message if is_failed else None,
                )
                if created_board_document is not None and not is_failed:
                    await self._share_board_result_to_feishu_chat(request, created_board_document, completed_task)
                archive_results = await self._archive_artifact_to_bitable(request, response, trace_events)
                if archive_results and response.artifact is not None:
                    response.artifact = response.artifact.model_copy(update={"bitable_archive_results": archive_results})
                response.events = self._events_from_traces(trace_events)
                await self._publish_chat_result(request, response)
            elif intent == AgentIntent.CHAT:
                reply = await self._llm.generate(
                    "你是 Eko 智能办公助手。请直接、友好地回答用户问题。若 RAG 知识库资料与问题相关，必须优先依据知识库资料回答；不要编造知识库未提供的信息。",
                    self._build_chat_prompt(request, runtime_turn.retrieved_context, route_result=route_result),
                )
                reply = self._clean_chat_reply(reply)
                response = AgentChatResponse(
                    session_id=request.session_id,
                    intent=AgentIntent.CHAT.value,
                    status="completed",
                    message=reply,
                    events=self._events_from_traces(trace_events),
                )
                await self._publish_chat_result(request, response)
            else:
                execution_request = request.model_copy(update={"planning_enabled": False})
                response = await self.chat(execution_request)
            yield AgentEventProtocol.result(response, response.message)
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent chat stream failed session=%s, error=%s", request.session_id, exc)
            response = AgentChatResponse(
                session_id=request.session_id,
                intent=intent.value,
                status="failed",
                message="处理失败，请稍后重试",
                events=AgentEventProtocol.from_traces(trace_events),
                error=str(exc),
            )
            yield AgentEventProtocol.failed(response, response.message, str(exc))

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

    async def _edit_current_document(
        self,
        request: AgentChatRequest,
        artifact: AgentChatArtifact,
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
        response = AgentChatResponse(
            session_id=request.session_id,
            intent=AgentIntent.DOCX.value,
            status="completed",
            message=message,
            artifact=updated_artifact,
        )
        archive_results = await self._archive_artifact_to_bitable(request, response)
        if archive_results and response.artifact is not None:
            response.artifact = response.artifact.model_copy(update={"bitable_archive_results": archive_results})
        return response

    async def _archive_artifact_to_bitable(
        self,
        request: AgentChatRequest,
        response: AgentChatResponse,
        trace_events: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        if self._bitable_service is None or response.artifact is None or response.status != "completed":
            return []
        try:
            archive_response = await self._bitable_service.archive_artifact(
                BitableArchiveRequest(
                    workspace_id=self._workspace_id_from_request(request),
                    session_id=request.session_id,
                    artifact=response.artifact.model_dump(),
                ),
                created_by=self._created_by_from_request(request),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bitable archive failed session=%s: %s", request.session_id, exc)
            if trace_events is not None:
                trace_events.append(
                    AgentTraceEvent(
                        type="artifact_archive_failed",
                        status="failed",
                        message="Bitable 归档失败，主任务已继续完成。",
                        data={"error": str(exc)},
                    )
                )
            return []

        if not archive_response.results:
            return []
        failed = [result for result in archive_response.results if result.status == "failed"]
        event_type = "artifact_archive_failed" if failed else "artifact_archived"
        status = "failed" if failed else "completed"
        message = "Bitable 归档失败，主任务已继续完成。" if failed else "生成产物已归档到 Bitable。"
        if trace_events is not None:
            trace_events.append(
                AgentTraceEvent(
                    type=event_type,
                    status=status,  # type: ignore[arg-type]
                    message=message,
                    data={"results": [result.model_dump() for result in archive_response.results]},
                )
            )
        return [result.model_dump() for result in archive_response.results]

    def _workspace_id_from_request(self, request: AgentChatRequest) -> str:
        if request.sender and isinstance(request.sender.get("workspace_id"), str):
            return str(request.sender["workspace_id"])
        return settings.BITABLE_DEFAULT_WORKSPACE_ID

    def _created_by_from_request(self, request: AgentChatRequest) -> str | None:
        if not request.sender:
            return None
        raw = (
            request.sender.get("platform_user_id")
            or request.sender.get("sender_open_id")
            or request.sender.get("sender_union_id")
        )
        return str(raw) if raw else None

    def _tool_call_message(self, intent: AgentIntent) -> str:
        if intent == AgentIntent.DOCX:
            return "正在处理。"
        if intent == AgentIntent.PPT:
            return "正在处理。"
        if intent == AgentIntent.BOARD:
            return "正在处理。"
        return "好的，我现在直接回复这个问题。"

    def _forced_or_classified_intent(self, request: AgentChatRequest) -> AgentIntent:
        raw_intent = (request.forced_intent or "").strip().lower()
        if not raw_intent:
            return AgentIntent.UNKNOWN
        try:
            return AgentIntent(raw_intent)
        except ValueError:
            logger.warning("Unsupported forced intent ignored session=%s forced_intent=%s", request.session_id, raw_intent)
            return AgentIntent.UNKNOWN

    def _extract_feishu_chat_id(self, session_id: str) -> str | None:
        parts = session_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "feishu":
            return None
        return parts[1] or None

    def _extract_feishu_message_id(self, session_id: str) -> str | None:
        parts = session_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "feishu":
            return None
        return parts[2] or None

    async def _feishu_session_was_app_mention(self, session_id: str, chat_id: str) -> bool:
        message_id = self._extract_feishu_message_id(session_id)
        if not message_id:
            return False
        try:
            raw = await self._feishu.get_message(message_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Verify Feishu source mention failed session=%s message=%s: %s", session_id, message_id, exc)
            return False
        if not isinstance(raw, dict):
            return False
        if raw.get("chat_id") != chat_id:
            return False
        bot_open_id = None
        if hasattr(self._feishu, "get_bot_open_id"):
            try:
                bot_open_id = self._feishu.get_bot_open_id()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Load Feishu bot open_id for source mention check failed session=%s: %s", session_id, exc)
        return FeishuEventProcessor.message_mentions_app(raw, settings.FEISHU_APP_ID, bot_open_id=bot_open_id)

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
        if not await self._feishu_session_was_app_mention(request.session_id, chat_id):
            logger.info("Skip Feishu document link because source message did not mention app session=%s", request.session_id)
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
        if not await self._feishu_session_was_app_mention(request.session_id, chat_id):
            logger.info("Skip Feishu PPT link because source message did not mention app session=%s", request.session_id)
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
            archive_results = await self._archive_artifact_to_bitable(request, response)
            if archive_results and response.artifact is not None:
                response.artifact = response.artifact.model_copy(update={"bitable_archive_results": archive_results})
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
