from __future__ import annotations

from typing import Any

from app.modules.agent.schemas import AgentEventV1, AgentTaskPlan, AgentTraceEvent


class AgentEventProtocol:
    """Single Agent event protocol for API responses and SSE streams."""

    @staticmethod
    def from_trace(trace: AgentTraceEvent) -> AgentEventV1:
        event_map = {
            "turn_started": "turn.started",
            "context_loaded": "context.loaded",
            "retrieval_started": "retrieval.started",
            "retrieval_completed": "retrieval.completed",
            "plan_created": "plan.created",
            "tool_selected": "tool.selected",
            "tool_started": "tool.started",
            "tool_completed": "tool.completed",
        }
        status_map = {
            "pending": "pending",
            "in_progress": "running",
            "completed": "completed",
            "blocked": "blocked",
            "failed": "failed",
        }
        return AgentEventV1(
            event=event_map.get(trace.type, "result.created"),  # type: ignore[arg-type]
            status=status_map.get(trace.status, "completed"),  # type: ignore[arg-type]
            message=trace.message,
            payload=trace.data,
        )

    @staticmethod
    def from_traces(traces: list[AgentTraceEvent]) -> list[AgentEventV1]:
        return [AgentEventProtocol.from_trace(trace) for trace in traces]

    @staticmethod
    def start(planning_enabled: bool) -> dict[str, Any]:
        return AgentEventV1(
            event="turn.started",
            status="running",
            message=(
                "收到。我先理解你的任务，并拆成可以执行的步骤。"
                if planning_enabled
                else "收到。任务理解与规划已关闭，我会直接执行。"
            ),
            payload={"planning_enabled": planning_enabled},
        ).model_dump()

    @staticmethod
    def intent(intent: str, message: str | None = None) -> dict[str, Any]:
        return AgentEventV1(
            event="intent.recognized",
            status="completed",
            message=message or f"我判断这次要走 {intent} 能力。",
            payload={"intent": intent},
        ).model_dump()

    @staticmethod
    def plan(plan: AgentTaskPlan, message: str | None = None) -> dict[str, Any]:
        return AgentEventV1(
            event="plan.created",
            status="completed",
            message=message or "规划完成。下面按这些子任务执行。",
            payload={"plan": plan.model_dump()},
        ).model_dump()

    @staticmethod
    def plan_progress(plan: AgentTaskPlan) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if plan.summary:
            events.append(
                AgentEventV1(
                    event="plan.summary",
                    status="completed",
                    message=plan.summary,
                    payload={"summary": plan.summary},
                ).model_dump()
            )
        for index, step in enumerate(plan.steps, start=1):
            events.append(
                AgentEventV1(
                    event="plan.step",
                    status="completed",
                    message=f"{index}. {step.title}",
                    payload={"index": index, "step": step.model_dump()},
                ).model_dump()
            )
        return events

    @staticmethod
    def tool_started(intent: str, tool: str, message: str) -> dict[str, Any]:
        return AgentEventV1(
            event="tool.started",
            status="running",
            message=message,
            payload={"intent": intent, "tool": tool},
        ).model_dump()

    @staticmethod
    def clarification(intent: str, plan: AgentTaskPlan, message: str) -> dict[str, Any]:
        return AgentEventV1(
            event="clarification.requested",
            status="blocked",
            message=message,
            payload={"intent": intent, "plan": plan.model_dump(), "questions": plan.questions},
        ).model_dump()

    @staticmethod
    def result(response: Any, message: str) -> dict[str, Any]:
        payload = response.model_dump() if hasattr(response, "model_dump") else response
        return AgentEventV1(
            event="result.created",
            status="completed",
            message=message,
            payload={"response": payload},
        ).model_dump()

    @staticmethod
    def failed(response: Any, message: str, error: str) -> dict[str, Any]:
        payload = response.model_dump() if hasattr(response, "model_dump") else response
        return AgentEventV1(
            event="turn.failed",
            status="failed",
            message=message,
            payload={"response": payload, "error": error},
        ).model_dump()
