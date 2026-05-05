from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket

from app.modules.sync.dependencies import get_sync_service
from app.modules.sync.schemas import SyncChannelSchema, SyncContextSelectionRequest
from app.modules.sync.service import SyncService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/ws/{session_id}",
    response_model=ApiResponse[SyncChannelSchema],
    summary="同步通道骨架",
)
async def get_sync_channel(
    session_id: str,
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
) -> ApiResponse[SyncChannelSchema]:
    return ApiResponse.success(sync_service.get_channel(session_id))


@router.get(
    "/sessions",
    summary="会话列表",
)
async def list_sync_sessions(
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    return ApiResponse.success(await sync_service.list_sessions()).model_dump()


@router.get(
    "/sessions/{session_id}",
    summary="会话详情",
)
async def get_sync_session(
    session_id: str,
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    session = await sync_service.get_session(session_id)
    return ApiResponse.success(session).model_dump()


@router.delete(
    "/sessions/{session_id}",
    summary="删除会话",
)
async def delete_sync_session(
    session_id: str,
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    deleted = await sync_service.delete_session(session_id)
    return ApiResponse.success({"session_id": session_id, "deleted": deleted}).model_dump()


@router.post(
    "/sessions/{session_id}/context/selection",
    summary="选择上下文并运行 Agent",
)
async def select_context_and_run(
    session_id: str,
    request: SyncContextSelectionRequest,
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
) -> dict[str, object]:
    from app.modules.agent.schemas import AgentChatRequest, AgentContext, ChatMessage
    from app.modules.agent.service import AgentService
    from app.modules.aippt.dependencies import get_aippt_service
    from app.core.llm_client import get_llm_client
    from app.modules.canvas.dependencies import get_canvas_service
    from app.modules.document.dependencies import get_document_service
    from app.modules.feishu.dependencies import get_feishu_service

    session = await sync_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    start = min(request.start_index, request.end_index)
    end = max(request.start_index, request.end_index)
    candidates = session.context_messages
    if not candidates:
        selected = []
    else:
        selected = candidates[start : end + 1]

    await sync_service.mark_session_running(session_id, context_size=len(selected))
    llm_client = get_llm_client()
    feishu_service = get_feishu_service()
    agent_service = AgentService(
        llm_client=llm_client,
        feishu_service=feishu_service,
        document_service=get_document_service(llm_client=llm_client, feishu_service=feishu_service),
        aippt_service=get_aippt_service(),
        canvas_service=get_canvas_service(),
        sync_service=sync_service,
    )
    response = await agent_service.chat(
        AgentChatRequest(
            session_id=session_id,
            message=session.instruction or "请基于选中的群聊上下文继续回复。",
            context=AgentContext(
                chat_history=[
                    ChatMessage(role=message.role, content=message.content)
                    for message in selected
                ]
            ),
        )
    )
    return ApiResponse.success(response).model_dump()


@router.websocket("/ws/session/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: str,
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
) -> None:
    await sync_service.connect(session_id, websocket)
