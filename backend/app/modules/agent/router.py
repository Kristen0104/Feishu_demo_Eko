from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.agent.dependencies import get_agent_service
from app.modules.agent.schemas import AgentTaskSchema
from app.modules.agent.service import AgentService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.post(
    "/tasks",
    response_model=ApiResponse[AgentTaskSchema],
    summary="Agent 任务骨架",
)
async def create_agent_task(
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> ApiResponse[AgentTaskSchema]:
    return ApiResponse.success(agent_service.create_task())
