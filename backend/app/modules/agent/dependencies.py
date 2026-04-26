from __future__ import annotations

from app.modules.agent.service import AgentService


def get_agent_service() -> AgentService:
    return AgentService()
