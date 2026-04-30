from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.agent.dependencies import get_agent_service
from app.modules.agent.schemas import AgentChatRequest, AgentChatResponse, AgentTaskSchema
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


@router.post(
    "/chat",
    response_model=ApiResponse[AgentChatResponse],
    summary="Agent chat 路由",
)
async def agent_chat(
    request: AgentChatRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> ApiResponse[AgentChatResponse]:
    return ApiResponse.success(await agent_service.chat(request))
