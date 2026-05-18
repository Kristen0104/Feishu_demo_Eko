from __future__ import annotations

import logging
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph

from app.modules.agent.planner import PlannerAgent
from app.modules.agent.rag import AgentRAGRetriever
from app.modules.agent.schemas import AgentChatArtifact, AgentChatRequest, AgentIntent, IntentRouteResult
from app.modules.agent.state import AgentGraphState, AgentTurnState
from app.modules.agent.tools import AgentToolRegistry

logger = logging.getLogger(__name__)


class AgentRuntime:
    """LangGraph-backed pre-execution runtime for every Agent turn."""

    def __init__(
        self,
        *,
        planner: PlannerAgent,
        retriever: AgentRAGRetriever | None = None,
        tool_registry: AgentToolRegistry | None = None,
        tool_handlers: dict[str, Callable[..., Awaitable[Any]]] | None = None,
        planner_timeout_seconds: float = 6.0,
    ) -> None:
        self._planner = planner
        self._retriever = retriever or AgentRAGRetriever()
        self._tool_registry = tool_registry or AgentToolRegistry()
        self._tools = self._build_langchain_tools(tool_handlers or {})
        self._planner_timeout_seconds = planner_timeout_seconds
        self._graph = self._build_graph()

    async def prepare_turn(
        self,
        request: AgentChatRequest,
        *,
        routed_intent: AgentIntent,
        current_artifact: AgentChatArtifact | None,
        route_result: IntentRouteResult | None = None,
        execute_tools: bool = False,
    ) -> AgentTurnState:
        initial = AgentTurnState(
            session_id=request.session_id,
            user_id=self._resolve_user_id(request),
            user_message=request.message,
            routed_intent=routed_intent,
            route_result=route_result,
            request=request,
            current_artifact=current_artifact,
            execute_tools=execute_tools,
        )
        result = await self._graph.ainvoke({"turn": initial})
        return result["turn"]

    def tool_names(self) -> list[str]:
        return self._tool_registry.names()

    def _build_graph(self):  # type: ignore[no-untyped-def]
        graph = StateGraph(AgentGraphState)
        graph.add_node("context", self._context_node)
        graph.add_node("intent_route", self._intent_route_node)
        graph.add_node("clarification_gate", self._clarification_gate_node)
        graph.add_node("retrieval", self._retrieval_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("tool_execute", self._tool_execute_node)
        graph.set_entry_point("context")
        graph.add_edge("context", "intent_route")
        graph.add_edge("intent_route", "clarification_gate")
        graph.add_conditional_edges("clarification_gate", self._route_after_clarification, {"retrieval": "retrieval", "end": END})
        graph.add_edge("retrieval", "planner")
        graph.add_conditional_edges("planner", self._route_after_planner, {"tool_execute": "tool_execute", "end": END})
        graph.add_edge("tool_execute", END)
        return graph.compile()

    async def _context_node(self, state: AgentGraphState) -> AgentGraphState:
        turn = state["turn"]
        turn.add_event("turn_started", "收到用户输入，开始一次 Agent 回合。")
        turn.add_event(
            "context_loaded",
            "已装载会话上下文、当前产物和可用工具。",
            data={
                "session_id": turn.session_id,
                "intent": turn.routed_intent.value,
                "current_artifact": turn.current_artifact.kind if turn.current_artifact else None,
                "tools": self._tool_registry.names(),
            },
        )
        return {"turn": turn}

    async def _intent_route_node(self, state: AgentGraphState) -> AgentGraphState:
        turn = state["turn"]
        route = turn.route_result or IntentRouteResult(
            intent=turn.routed_intent.value if turn.routed_intent in {AgentIntent.CHAT, AgentIntent.DOCX, AgentIntent.PPT, AgentIntent.BOARD} else "chat",
            primary_tool=self._default_tool_candidates(turn.routed_intent)[0],
            confidence=1.0,
            reason="legacy_route",
        )
        turn.route_result = route
        try:
            turn.routed_intent = AgentIntent(route.intent)
        except ValueError:
            turn.routed_intent = AgentIntent.CHAT
        return {"turn": turn}

    async def _clarification_gate_node(self, state: AgentGraphState) -> AgentGraphState:
        turn = state["turn"]
        route = turn.route_result
        if route is None or not route.needs_clarification:
            return {"turn": turn}
        question = route.clarification_question or "请确认你希望我执行哪种动作。"
        turn.clarification_requested = True
        turn.add_event(
            "clarification_requested",
            question,
            status="blocked",
            data={
                "intent": route.intent,
                "primary_tool": route.primary_tool,
                "intent_candidates": [candidate.model_dump() for candidate in route.candidates],
                "clarification_options": [option.model_dump() for option in route.clarification_options],
                "pending_route": route.pending_route,
                "questions": [question],
            },
        )
        return {"turn": turn}

    def _route_after_clarification(self, state: AgentGraphState) -> str:
        return "end" if state["turn"].clarification_requested else "retrieval"

    async def _tool_execute_node(self, state: AgentGraphState) -> AgentGraphState:
        turn = state["turn"]
        if turn.plan is None:
            return {"turn": turn}

        step = next((candidate for candidate in turn.plan.steps if candidate.tool in self._tools), None)
        if step is None or step.tool is None:
            return {"turn": turn}

        turn.selected_tool = step.tool
        turn.add_event(
            "tool_selected",
            f"已根据计划选择工具：{step.tool}。",
            data={"tool": step.tool, "step": step.model_dump()},
        )
        tool = self._tools[step.tool]
        payload = dict(step.input)
        if "instruction" not in payload:
            payload["instruction"] = turn.user_message
        payload.setdefault("session_id", turn.session_id)
        if step.tool in {"docx", "board"} and turn.request.context and turn.request.context.chat_history:
            payload.setdefault(
                "chat_history",
                [message.model_dump() for message in turn.request.context.chat_history],
            )
        if turn.retrieved_context:
            payload.setdefault("retrieved_context", [chunk.model_dump() for chunk in turn.retrieved_context])
        if step.tool == "bitable_search":
            payload.setdefault("query", turn.user_message)
        if step.tool == "bitable_schema":
            payload.setdefault("workspace_id", "Feishu_demo_Eko")
        if step.tool in {"bitable_schema", "bitable_search", "bitable_archive"}:
            payload.setdefault("created_by", turn.user_id)
        if turn.request.sharing_url:
            payload.setdefault("sharing_url", turn.request.sharing_url)
        if turn.current_artifact is not None and turn.current_artifact.sharing_url:
            payload.setdefault("sharing_url", turn.current_artifact.sharing_url)
        turn.add_event("tool_started", f"开始调用工具：{step.tool}。", status="in_progress", data={"tool": step.tool, "input": payload})
        result = await tool.ainvoke(payload)
        turn.tool_results.append({"tool": step.tool, "result": result})
        step.status = "completed"
        turn.add_event("tool_completed", f"工具 {step.tool} 调用完成。", data={"tool": step.tool, "result": result})
        return {"turn": turn}

    def _route_after_planner(self, state: AgentGraphState) -> str:
        turn = state["turn"]
        if turn.plan is None:
            return "end"
        if not turn.execute_tools:
            return "end"
        has_executable_tool = any(step.tool in self._tools for step in turn.plan.steps if step.tool)
        return "tool_execute" if has_executable_tool else "end"

    async def _retrieval_node(self, state: AgentGraphState) -> AgentGraphState:
        turn = state["turn"]
        chunks = await self._retriever.retrieve(turn.request, current_artifact=turn.current_artifact)
        turn.retrieved_context = chunks
        return {"turn": turn}

    async def _planner_node(self, state: AgentGraphState) -> AgentGraphState:
        turn = state["turn"]
        context = turn.request.context
        try:
            if turn.request.planning_enabled:
                turn.plan = await asyncio.wait_for(
                    self._planner.create_plan(
                        turn.user_message,
                        routed_intent=turn.routed_intent,
                        context=context,
                        retrieved_context=turn.retrieved_context,
                        available_tools=self._tool_registry.list_specs(),
                    ),
                    timeout=self._planner_timeout_seconds,
                )
                if not turn.plan.tool_candidates:
                    turn.plan.tool_candidates = self._default_tool_candidates(turn.routed_intent)
                if not turn.plan.visible_summary:
                    turn.plan.visible_summary = turn.plan.summary
                turn.add_event(
                    "plan_created",
                    turn.plan.visible_summary or turn.plan.summary,
                    data={"plan": turn.plan.model_dump()},
                )
            else:
                turn.add_event("plan_skipped", "本次请求关闭了规划，直接进入执行。")
        except Exception as exc:  # noqa: BLE001
            logger.warning("AgentRuntime planner failed session=%s: %s", turn.session_id, exc)
            turn.errors.append(str(exc))
            turn.plan = self._planner._fallback_plan(turn.user_message, turn.routed_intent)
            turn.add_event(
                "plan_created",
                turn.plan.visible_summary or turn.plan.summary,
                data={"plan": turn.plan.model_dump(), "fallback": True},
            )
        return {"turn": turn}

    def _default_tool_candidates(self, intent: AgentIntent) -> list[str]:
        if intent == AgentIntent.DOCX:
            return ["knowledge_search", "docx", "sync"]
        if intent == AgentIntent.PPT:
            return ["knowledge_search", "ppt", "sync"]
        if intent == AgentIntent.BOARD:
            return ["knowledge_search", "board", "sync"]
        return ["chat"]

    def _resolve_user_id(self, request: AgentChatRequest) -> str | None:
        if not request.sender:
            return None
        raw = request.sender.get("platform_user_id") or request.sender.get("sender_open_id") or request.sender.get("sender_union_id")
        return str(raw) if raw else None

    def _build_langchain_tools(
        self,
        handlers: dict[str, Callable[..., Awaitable[Any]]],
    ) -> dict[str, StructuredTool]:
        tools: dict[str, StructuredTool] = {}
        for name, handler in handlers.items():
            spec = self._tool_registry.get(name)
            if spec is None:
                continue
            tools[name] = StructuredTool.from_function(
                coroutine=handler,
                name=spec.name,
                description=spec.description,
            )
        return tools
