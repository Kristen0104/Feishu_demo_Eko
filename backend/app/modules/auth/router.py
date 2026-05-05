from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import AuthContext, get_auth_context
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.schemas import (
    AuthTokenSchema,
    AuthUserSchema,
    AuthLoginRequest,
    AuthRegisterRequest,
    FeishuCallbackRequest,
    FeishuLoginRequest,
    FeishuLoginUrlSchema,
)
from app.modules.auth.service import AuthService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=ApiResponse[AuthTokenSchema],
    summary="邮箱密码注册",
)
async def register(
    payload: AuthRegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthTokenSchema]:
    return ApiResponse.success(await auth_service.register_with_password(payload))


@router.post(
    "/login",
    response_model=ApiResponse[AuthTokenSchema],
    summary="邮箱密码登录",
)
async def login(
    payload: AuthLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthTokenSchema]:
    return ApiResponse.success(await auth_service.login_with_password(payload))


@router.get(
    "/feishu/login-url",
    response_model=ApiResponse[FeishuLoginUrlSchema],
    summary="生成飞书登录授权 URL",
)
async def get_feishu_login_url(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    redirect_uri: str | None = None,
) -> ApiResponse[FeishuLoginUrlSchema]:
    return ApiResponse.success(await auth_service.create_feishu_login_url(redirect_uri=redirect_uri))


@router.post(
    "/feishu/login",
    response_model=ApiResponse[AuthTokenSchema],
    summary="Feishu OAuth 登录",
)
async def feishu_login(
    payload: FeishuLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthTokenSchema]:
    return ApiResponse.success(await auth_service.login_with_feishu(payload))


@router.get(
    "/feishu/callback",
    response_model=ApiResponse[AuthTokenSchema],
    summary="飞书 OAuth 回调登录",
)
async def feishu_callback(
    code: str,
    state: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    redirect_uri: str | None = None,
) -> ApiResponse[AuthTokenSchema]:
    return ApiResponse.success(
        await auth_service.login_with_feishu_callback(
            FeishuCallbackRequest(code=code, state=state, redirect_uri=redirect_uri)
        )
    )


@router.get(
    "/me",
    response_model=ApiResponse[AuthUserSchema],
    summary="当前登录用户",
)
async def get_current_user(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthUserSchema]:
    return ApiResponse.success(await auth_service.get_current_user(auth_context))
