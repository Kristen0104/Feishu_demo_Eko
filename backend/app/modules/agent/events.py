from __future__ import annotations

from typing import Any

from app.modules.agent.schemas import AgentEventV1, AgentTaskPlan, AgentTraceEvent

EVENT_CHANNEL_MAP: dict[str, tuple[str, str]] = {
    "turn.started": ("status", "user"),
    "intent.recognized": ("status", "detail"),
    "context.loaded": ("sources", "detail"),
    "retrieval.started": ("status", "detail"),
    "retrieval.completed": ("sources", "detail"),
    "source.bitable.started": ("sources", "detail"),
    "source.bitable.completed": ("sources", "detail"),
    "source.bitable.empty": ("sources", "detail"),
    "source.bitable.failed": ("sources", "detail"),
    "plan.created": ("plan", "detail"),
    "plan.summary": ("plan", "detail"),
    "plan.step": ("plan", "detail"),
    "tool.selected": ("log", "debug"),
    "tool.started": ("status", "detail"),
    "tool.completed": ("log", "debug"),
    "clarification.requested": ("chat", "user"),
    "artifact.archived": ("artifact", "detail"),
    "artifact.archive_failed": ("artifact", "detail"),
    "result.created": ("chat", "user"),
    "turn.failed": ("error", "user"),
}


class AgentEventProtocol:
    """Single Agent event protocol for API responses and SSE streams."""

    @staticmethod
    def _event(
        *,
        event: str,
        status: str = "completed",
        message: str,
        payload: dict[str, Any] | None = None,
        channel: str | None = None,
        visibility: str | None = None,
    ) -> AgentEventV1:
        mapped_channel, mapped_visibility = EVENT_CHANNEL_MAP.get(event, ("log", "detail"))
        return AgentEventV1(
            event=event,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            channel=channel or mapped_channel,  # type: ignore[arg-type]
            visibility=visibility or mapped_visibility,  # type: ignore[arg-type]
            message=message,
            payload=payload or {},
        )

    @staticmethod
    def from_trace(trace: AgentTraceEvent) -> AgentEventV1:
        event_map = {
            "turn_started": "turn.started",
            "context_loaded": "context.loaded",
            "retrieval_started": "retrieval.started",
            "retrieval_completed": "retrieval.completed",
            "source_bitable_started": "source.bitable.started",
            "source_bitable_completed": "source.bitable.completed",
            "source_bitable_empty": "source.bitable.empty",
            "source_bitable_failed": "source.bitable.failed",
            "artifact_archived": "artifact.archived",
            "artifact_archive_failed": "artifact.archive_failed",
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
        return AgentEventProtocol._event(
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
        return AgentEventProtocol._event(
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
        return AgentEventProtocol._event(
            event="intent.recognized",
            status="completed",
            message=message or f"我判断这次要走 {intent} 能力。",
            payload={"intent": intent},
        ).model_dump()

    @staticmethod
    def plan(plan: AgentTaskPlan, message: str | None = None) -> dict[str, Any]:
        return AgentEventProtocol._event(
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
                AgentEventProtocol._event(
                    event="plan.summary",
                    status="completed",
                    message=plan.summary,
                    payload={"summary": plan.summary},
                ).model_dump()
            )
        for index, step in enumerate(plan.steps, start=1):
            events.append(
                AgentEventProtocol._event(
                    event="plan.step",
                    status="completed",
                    message=f"{index}. {step.title}",
                    payload={"index": index, "step": step.model_dump()},
                ).model_dump()
            )
        return events

    @staticmethod
    def tool_started(intent: str, tool: str, message: str) -> dict[str, Any]:
        return AgentEventProtocol._event(
            event="tool.started",
            status="running",
            message=message,
            payload={"intent": intent, "tool": tool},
        ).model_dump()

    @staticmethod
    def clarification(intent: str, plan: AgentTaskPlan, message: str) -> dict[str, Any]:
        return AgentEventProtocol._event(
            event="clarification.requested",
            status="blocked",
            message=message,
            payload={"intent": intent, "plan": plan.model_dump(), "questions": plan.questions},
        ).model_dump()

    @staticmethod
    def _normalize_result_value(value: Any) -> str:
        raw = value.value if hasattr(value, "value") else value
        return str(raw or "").strip().lower()

    @staticmethod
    def _result_channel(payload: Any) -> tuple[str, str]:
        if not isinstance(payload, dict):
            return "chat", "user"

        if AgentEventProtocol._normalize_result_value(payload.get("status")) == "failed":
            return "error", "user"

        artifact = payload.get("artifact")
        if hasattr(artifact, "model_dump"):
            artifact = artifact.model_dump()
        if isinstance(artifact, dict):
            kind = AgentEventProtocol._normalize_result_value(artifact.get("kind"))
            if kind in {"docx", "ppt", "board"}:
                return "artifact", "user"

        intent = AgentEventProtocol._normalize_result_value(payload.get("intent"))
        if intent in {"docx", "ppt", "board"}:
            return "artifact", "user"

        return "chat", "user"

    @staticmethod
    def result(response: Any, message: str) -> dict[str, Any]:
        payload = response.model_dump() if hasattr(response, "model_dump") else response
        channel, visibility = AgentEventProtocol._result_channel(payload)
        return AgentEventProtocol._event(
            event="result.created",
            status="completed",
            channel=channel,
            visibility=visibility,
            message=message,
            payload={"response": payload},
        ).model_dump()

    @staticmethod
    def failed(response: Any, message: str, error: str) -> dict[str, Any]:
        payload = response.model_dump() if hasattr(response, "model_dump") else response
        return AgentEventProtocol._event(
            event="turn.failed",
            status="failed",
            message=message,
            payload={"response": payload, "error": error},
        ).model_dump()
