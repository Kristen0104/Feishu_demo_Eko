from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config import settings
from app.core.security import AuthContext, get_auth_context
from app.modules.agent.dependencies import get_agent_service
from app.modules.agent.schemas import AgentChatRequest, AgentChatResponse, AgentTaskSchema
from app.modules.agent.service import AgentService
from app.shared.responses import ApiResponse

router = APIRouter()


def _with_authenticated_sender(request: AgentChatRequest, auth_context: AuthContext) -> AgentChatRequest:
    sender = dict(request.sender or {})
    sender["platform_user_id"] = auth_context.user_id
    if auth_context.feishu_user_id:
        sender["sender_open_id"] = auth_context.feishu_user_id
    sender.setdefault("workspace_id", settings.BITABLE_DEFAULT_WORKSPACE_ID)
    return request.model_copy(update={"sender": sender, "forced_intent": None})


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
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> ApiResponse[AgentChatResponse]:
    return ApiResponse.success(await agent_service.chat(_with_authenticated_sender(request, auth_context)))


@router.post(
    "/chat/stream",
    summary="Agent chat 流式路由",
)
async def agent_chat_stream(
    request: AgentChatRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> StreamingResponse:
    authenticated_request = _with_authenticated_sender(request, auth_context)

    async def event_stream():
        async for event in agent_service.chat_stream_events(authenticated_request):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
