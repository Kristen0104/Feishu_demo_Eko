from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import AuthContext, get_auth_context
from app.modules.team.dependencies import get_team_service
from app.modules.team.schemas import TeamInviteRequest, TeamMemberSchema
from app.modules.team.service import TeamService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/members",
    response_model=ApiResponse[list[TeamMemberSchema]],
    summary="获取团队成员列表",
)
async def list_members(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    team_service: Annotated[TeamService, Depends(get_team_service)],
) -> ApiResponse[list[TeamMemberSchema]]:
    return ApiResponse.success(await team_service.list_members(auth_context))


@router.post(
    "/members/invite",
    response_model=ApiResponse[TeamMemberSchema],
    summary="按邮箱邀请团队成员",
)
async def invite_member(
    payload: TeamInviteRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    team_service: Annotated[TeamService, Depends(get_team_service)],
) -> ApiResponse[TeamMemberSchema]:
    return ApiResponse.success(await team_service.invite_member(auth_context, payload))


@router.delete(
    "/members/{member_id}",
    response_model=ApiResponse[None],
    summary="移除团队成员",
)
async def remove_member(
    member_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    team_service: Annotated[TeamService, Depends(get_team_service)],
) -> ApiResponse[None]:
    await team_service.remove_member(auth_context, member_id)
    return ApiResponse.success()

