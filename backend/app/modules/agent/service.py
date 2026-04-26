from __future__ import annotations

from app.modules.agent.schemas import AgentTaskSchema


class AgentService:
    def create_task(self) -> AgentTaskSchema:
        return AgentTaskSchema(task_id="stub-task")
