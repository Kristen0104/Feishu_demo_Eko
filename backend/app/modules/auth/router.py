from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import AuthContext, get_auth_context
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.schemas import AuthTokenSchema, AuthUserSchema, FeishuLoginRequest
from app.modules.auth.service import AuthService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.post(
    "/feishu/login",
    response_model=ApiResponse[AuthTokenSchema],
    summary="Feishu OAuth 登录骨架",
)
async def feishu_login(
    payload: FeishuLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthTokenSchema]:
    return ApiResponse.success(auth_service.login_with_feishu(payload))


@router.get(
    "/me",
    response_model=ApiResponse[AuthUserSchema],
    summary="当前登录用户骨架",
)
async def get_current_user(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthUserSchema]:
    return ApiResponse.success(auth_service.get_current_user(auth_context))
