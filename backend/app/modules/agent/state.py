from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field

from app.modules.agent.schemas import (
    AgentChatArtifact,
    AgentChatRequest,
    AgentIntent,
    IntentRouteResult,
    AgentRetrievedContext,
    AgentTraceEvent,
)


class AgentTurnState(BaseModel):
    session_id: str
    user_id: str | None = None
    user_message: str
    routed_intent: AgentIntent
    route_result: IntentRouteResult | None = None
    clarification_requested: bool = False
    request: AgentChatRequest
    current_artifact: AgentChatArtifact | None = None
    execute_tools: bool = False
    retrieved_context: list[AgentRetrievedContext] = Field(default_factory=list)
    selected_tool: str | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def add_event(
        self,
        event_type: str,
        message: str,
        *,
        status: str = "completed",
        data: dict[str, Any] | None = None,
    ) -> None:
        self.trace_events.append(
            AgentTraceEvent(
                type=event_type,
                status=status,  # type: ignore[arg-type]
                message=message,
                data=data or {},
            )
        )


class AgentGraphState(TypedDict, total=False):
    turn: AgentTurnState
