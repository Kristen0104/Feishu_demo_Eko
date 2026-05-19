from __future__ import annotations

from typing import Any

from app.modules.agent.schemas import AgentEventV1, AgentTraceEvent

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
    "tool.selected": ("log", "debug"),
    "tool.started": ("status", "detail"),
    "tool.completed": ("log", "debug"),
    "clarification.requested": ("chat", "user"),
    "artifact.archived": ("artifact", "detail"),
    "artifact.archive_failed": ("artifact", "detail"),
    "artifact.delta": ("artifact", "user"),
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
            "tool_selected": "tool.selected",
            "tool_started": "tool.started",
            "tool_completed": "tool.completed",
            "intent_recognized": "intent.recognized",
            "clarification_requested": "clarification.requested",
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
        return [
            AgentEventProtocol.from_trace(trace)
            for trace in traces
            if trace.type in {"clarification_requested", "artifact_archived", "artifact_archive_failed"}
        ]

    @staticmethod
    def start(planning_enabled: bool) -> dict[str, Any]:
        return AgentEventProtocol._event(
            event="turn.started",
            status="running",
            message="",
            payload={"planning_enabled": planning_enabled},
        ).model_dump()

    @staticmethod
    def intent(intent: str, message: str | None = None) -> dict[str, Any]:
        return AgentEventProtocol._event(
            event="intent.recognized",
            status="completed",
            message=message or "",
            payload={"intent": intent},
        ).model_dump()

    @staticmethod
    def tool_started(intent: str, tool: str, message: str) -> dict[str, Any]:
        return AgentEventProtocol._event(
            event="tool.started",
            status="running",
            message=message,
            payload={"intent": intent, "tool": tool},
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
    def artifact_delta(session_id: str, *, kind: str, chunk: str, content: str) -> dict[str, Any]:
        return AgentEventProtocol._event(
            event="artifact.delta",
            status="running",
            channel="artifact",
            visibility="user",
            message="文档生成中。",
            payload={
                "session_id": session_id,
                "chunk": chunk,
                "content": content,
                "artifact": {
                    "kind": kind,
                    "content": content,
                    "status": "running",
                    "current_step": "生成文档",
                },
            },
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
