from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.sync.dependencies import get_sync_service
from app.modules.sync.schemas import SyncChannelSchema
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
