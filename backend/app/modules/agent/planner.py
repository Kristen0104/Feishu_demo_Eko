from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.llm_client import LLMClient
from app.modules.agent.schemas import (
    AgentContext,
    AgentIntent,
    AgentPlanFinalOutput,
    AgentPlanStep,
    AgentRetrievedContext,
    AgentTaskPlan,
)
from app.modules.agent.tools import ToolSpec

logger = logging.getLogger(__name__)

_CONTEXT_SELECTION_HINT_RE = re.compile(r"(根据|基于).*(聊天记录|上下文|群聊消息|刚才讨论)|聊天记录|群聊消息|刚才讨论|上下文")


class PlannerAgent:
    """Turns user intent into a structured, executable task plan."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def create_plan(
        self,
        message: str,
        *,
        routed_intent: AgentIntent,
        context: AgentContext | None = None,
        retrieved_context: list[AgentRetrievedContext] | None = None,
        available_tools: list[ToolSpec] | None = None,
    ) -> AgentTaskPlan:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            message,
            routed_intent=routed_intent,
            context=context,
            retrieved_context=retrieved_context or [],
            available_tools=available_tools or [],
        )

        try:
            result = await self._llm.generate(system_prompt, user_prompt, temperature=0.0)
            payload = self._normalize_payload(self._extract_json_payload(result))
            return AgentTaskPlan.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PlannerAgent failed to produce valid plan: %s", exc)
            return self._fallback_plan(message, routed_intent)

    def _build_system_prompt(self) -> str:
        return """你是 Eko 的 Agent Planner，负责将用户自然语言任务拆解为结构化、可执行、可追踪的执行计划。

核心职责：
1. 识别用户真正想完成的最终目标，而不是只匹配表面关键词。
2. 提取关键约束、上下文、缺失信息、默认假设和所需资源。
3. 将复杂任务拆解为有顺序、有依赖关系的子任务步骤。
4. 判断每一步是否需要工具调用，并给出工具名、输入和预期输出。
5. 只输出规划，不执行任务本身。

约束：
1. 只输出 JSON，不要 Markdown，不要解释。
2. 不要直接生成最终文档、PPT 或画板内容，只做规划。
3. 如果信息不足以可靠执行，设置 need_clarification=true，missing_info 写缺失项。
4. steps 必须按执行顺序排列，depends_on 只能引用前面已经出现的 step id。
5. step.type 只能使用 reasoning、tool_call、generation、validation、clarification。
6. step.status 默认 pending，执行中由运行时更新为 in_progress、completed、blocked 或 failed。
7. tool 可为空；需要工具时使用可用工具名，例如 chat、docx、ppt、ppt_create、ppt_edit、board、docx_edit、knowledge_search、bitable_schema、bitable_search、bitable_archive、artifact_lookup、sync。
8. visible_summary 必须是给用户看的中文摘要，风格接近 Claude Code / Codex：先说理解，再说计划，再说当前需要什么。
9. 重要：PPT 默认使用 template 模式继续执行，绝不为了“模板模式还是自由设计”发起澄清问题；只有用户原文明确写出“自由设计/free design/free_design”时才使用 free_design。
10. requires_context_selection 由你判断。只有当用户明确要求“基于聊天记录/上下文/刚才讨论/群聊消息”等历史消息来生成时，才设为 true；否则必须设为 false。
11. 当用户请求“结合项目表/排期/负责人/活动数据/状态/数据记录/Bitable/多维表格”时，应考虑 bitable_search；Bitable 查询失败不是任务失败，查询不到时继续使用聊天上下文和 RAG。

输出格式：
{
  "goal": "用户最终目标",
  "intent": "具体任务意图，例如 report_generation/travel_planning/doc_generation/ppt_generation/board_generation/chat",
  "task_complexity": "simple|medium|complex",
  "missing_info": [],
  "requires_context_selection": false,
  "need_clarification": false,
  "questions": [],
  "assumptions": [],
  "summary": "一句话概括计划",
  "visible_summary": "给用户看的中文计划摘要",
  "tool_candidates": ["可能会用到的工具名"],
  "steps": [
    {
      "id": "step_1",
      "title": "步骤标题",
      "description": "这一步要做什么",
      "type": "reasoning|tool_call|generation|validation|clarification",
      "status": "pending",
      "tool": null,
      "input": {},
      "expected_output": "这一步的可验证产出",
      "depends_on": []
    }
  ],
  "final_output": {
    "format": "最终输出格式",
    "requirements": []
  }
}"""

    def _build_user_prompt(
        self,
        message: str,
        *,
        routed_intent: AgentIntent,
        context: AgentContext | None,
        retrieved_context: list[AgentRetrievedContext],
        available_tools: list[ToolSpec],
    ) -> str:
        context_summary = ""
        if context is not None:
            context_summary = json.dumps(context.model_dump(), ensure_ascii=False)
        retrieved_summary = json.dumps([chunk.model_dump() for chunk in retrieved_context], ensure_ascii=False)
        tools_summary = json.dumps(
            [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
                for tool in available_tools
            ],
            ensure_ascii=False,
        )
        return (
            f"系统路由参考：{routed_intent.value}\n"
            f"用户消息：{message}\n"
            f"上下文 JSON：{context_summary or '{}'}\n\n"
            f"RAG 检索结果 JSON：{retrieved_summary or '[]'}\n\n"
            f"可用工具 JSON：{tools_summary or '[]'}\n\n"
            "请按指定 schema 输出 Planner JSON："
        )

    def _extract_json_payload(self, result: str) -> dict[str, Any]:
        stripped = result.strip()
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
        if fence_match:
            stripped = fence_match.group(1).strip()
        return json.loads(stripped)

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload.setdefault("task_complexity", "medium")
        payload.setdefault("missing_info", [])
        payload.setdefault("requires_context_selection", False)
        payload.setdefault("need_clarification", bool(payload.get("clarification_needed", False)))
        if "questions" not in payload:
            question = payload.get("clarification_question")
            payload["questions"] = [question] if isinstance(question, str) and question else []
        payload.setdefault("assumptions", [])
        payload.setdefault("summary", payload.get("goal", ""))
        payload.setdefault("visible_summary", payload.get("summary", payload.get("goal", "")))
        payload.setdefault("tool_candidates", [])
        payload.setdefault("final_output", {"format": "text", "requirements": []})

        normalized_steps: list[dict[str, Any]] = []
        for index, raw_step in enumerate(payload.get("steps", []), start=1):
            if not isinstance(raw_step, dict):
                continue
            step = dict(raw_step)
            step.setdefault("id", step.pop("step_id", f"step_{index}"))
            step.setdefault("title", step.get("name", f"步骤 {index}"))
            step.setdefault("description", step["title"])
            raw_tool = step.get("tool")
            step.setdefault("type", "tool_call" if raw_tool else "reasoning")
            if raw_tool == "none":
                step["tool"] = None
            step.setdefault("input", step.pop("inputs", {}))
            step.setdefault("expected_output", step["title"])
            step.setdefault("depends_on", [])
            step.setdefault("status", "pending")
            normalized_steps.append(step)
        payload["steps"] = normalized_steps
        return payload

    def _fallback_plan(self, message: str, routed_intent: AgentIntent) -> AgentTaskPlan:
        if routed_intent == AgentIntent.DOCX:
            return AgentTaskPlan(
                goal=message,
                intent="doc_generation",
                task_complexity="medium",
                requires_context_selection=False,
                summary="整理上下文并生成文档。",
                visible_summary="我理解你要生成一份文档。我会先梳理写作目标，再调用文档生成能力，最后同步结果。",
                tool_candidates=["docx", "sync"],
                assumptions=["默认使用当前会话上下文作为写作依据"],
                steps=[
                    AgentPlanStep(
                        id="step_1",
                        title="理解写作目标",
                        description="识别文档类型、主题和可用上下文。",
                        type="reasoning",
                        tool=None,
                        expected_output="明确文档目标和约束",
                    ),
                    AgentPlanStep(
                        id="step_2",
                        title="生成文档",
                        description="调用文档生成服务产出 Markdown 内容。",
                        type="generation",
                        tool="docx",
                        expected_output="Markdown 文档内容",
                        depends_on=["step_1"],
                    ),
                    AgentPlanStep(
                        id="step_3",
                        title="同步结果",
                        description="在飞书会话中回写文档链接或生成结果。",
                        type="tool_call",
                        tool="sync",
                        expected_output="飞书同步结果",
                        depends_on=["step_2"],
                    ),
                ],
                final_output=AgentPlanFinalOutput(format="markdown_document", requirements=["结构清晰", "符合用户主题"]),
            )
        if routed_intent == AgentIntent.PPT:
            return AgentTaskPlan(
                goal=message,
                intent="ppt_generation",
                task_complexity="medium",
                requires_context_selection=False,
                summary="整理展示目标并创建 AI PPT 任务。",
                visible_summary="我理解你要生成一份 PPT。我会默认使用模板模式，先梳理展示需求，再创建 PPT 任务并同步状态。",
                tool_candidates=["knowledge_search", "ppt", "sync"],
                assumptions=["默认使用 clean_business 风格"],
                steps=[
                    AgentPlanStep(
                        id="step_1",
                        title="梳理展示需求",
                        description="识别 PPT 主题、页数和展示风格。",
                        type="reasoning",
                        tool=None,
                        expected_output="PPT 生成参数",
                    ),
                    AgentPlanStep(
                        id="step_2",
                        title="创建 PPT 任务",
                        description="调用 AI PPT 服务创建后台生成任务。",
                        type="tool_call",
                        tool="ppt",
                        expected_output="PPT 后台任务",
                        depends_on=["step_1"],
                    ),
                    AgentPlanStep(
                        id="step_3",
                        title="同步任务状态",
                        description="向前端或飞书会话同步 PPT 任务进度。",
                        type="tool_call",
                        tool="sync",
                        expected_output="PPT 任务状态",
                        depends_on=["step_2"],
                    ),
                ],
                final_output=AgentPlanFinalOutput(format="ppt_file", requirements=["可下载", "状态可追踪"]),
            )
        if routed_intent == AgentIntent.BOARD:
            requires_context_selection = bool(_CONTEXT_SELECTION_HINT_RE.search(message))
            return AgentTaskPlan(
                goal=message,
                intent="board_generation",
                task_complexity="medium",
                requires_context_selection=requires_context_selection,
                summary="解析飞书目标并生成画板内容。",
                visible_summary=(
                    "我理解你要处理飞书画板。你这次明确要求基于聊天记录/上下文生成，请先选择消息记录，我再继续生成。"
                    if requires_context_selection
                    else "我理解你要处理飞书画板。我会先确认可写入目标，再生成画板内容，并同步结果。"
                ),
                tool_candidates=["feishu", "board", "sync"],
                assumptions=["如果没有 sharing_url，默认自动创建飞书画板文档"],
                steps=[
                    AgentPlanStep(
                        id="step_1",
                        title="解析飞书画板目标",
                        description="确认分享链接或自动创建可写入的飞书画板文档。",
                        type="tool_call",
                        tool="feishu",
                        expected_output="可写入的飞书画板目标",
                    ),
                    AgentPlanStep(
                        id="step_2",
                        title="生成并写入画板",
                        description="把用户需求转换为画板节点并写入飞书画板。",
                        type="tool_call",
                        tool="board",
                        expected_output="飞书画板节点",
                        depends_on=["step_1"],
                    ),
                    AgentPlanStep(
                        id="step_3",
                        title="同步画板结果",
                        description="回传画板链接、白板 ID 和执行摘要。",
                        type="tool_call",
                        tool="sync",
                        expected_output="画板链接和执行摘要",
                        depends_on=["step_2"],
                    ),
                ],
                final_output=AgentPlanFinalOutput(format="feishu_board", requirements=["包含画板链接", "可回溯执行结果"]),
            )
        return AgentTaskPlan(
            goal=message,
            intent="chat",
            task_complexity="simple",
            requires_context_selection=False,
            summary="直接回答用户问题。",
            visible_summary="我理解这是一次普通问答，会结合当前上下文直接回复。",
            tool_candidates=["chat"],
            steps=[
                AgentPlanStep(
                    id="step_1",
                    title="生成回复",
                    description="结合用户消息和上下文生成自然语言回复。",
                    type="generation",
                    tool="chat",
                    expected_output="自然语言回复",
                )
            ],
            final_output=AgentPlanFinalOutput(format="chat_message", requirements=["直接", "友好"]),
        )
