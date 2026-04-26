from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.workspace.dependencies import get_workspace_service
from app.modules.workspace.schemas import WorkspaceSchema
from app.modules.workspace.service import WorkspaceService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/{workspace_id}",
    response_model=ApiResponse[WorkspaceSchema],
    summary="工作区骨架",
)
async def get_workspace(
    workspace_id: str,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> ApiResponse[WorkspaceSchema]:
    return ApiResponse.success(workspace_service.get_workspace(workspace_id))
