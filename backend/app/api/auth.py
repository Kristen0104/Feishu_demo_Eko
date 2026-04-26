"""Authentication API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..modules.auth import AuthenticatedUser, build_authenticated_user, issue_user_token, upsert_feishu_user
from ..modules.auth.dependencies import get_current_user
from ..schemas.schemas import AuthLoginResponse, AuthMeResponse, AuthUserResponse, FeishuLoginRequest

# TODO(PRD-2.3): add Feishu OAuth code exchange and workspace creator linkage once frontend login flow is wired.
router = APIRouter()


@router.post("/feishu/login", response_model=AuthLoginResponse)
async def feishu_login(request: FeishuLoginRequest, db: AsyncSession = Depends(get_db)):
    if not request.feishu_open_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="feishu_open_id is required")

    user = await upsert_feishu_user(
        db=db,
        feishu_open_id=request.feishu_open_id,
        name=request.name or "飞书用户",
        avatar_url=request.avatar_url,
    )
    token = issue_user_token(user)
    auth_user = build_authenticated_user(user)
    return AuthLoginResponse(access_token=token, token_type="Bearer", user=auth_user)


@router.get("/me", response_model=AuthMeResponse)
async def me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return AuthMeResponse(
        user=AuthUserResponse(
            id=current_user.id,
            feishu_open_id=current_user.feishu_open_id,
            name=current_user.name,
            avatar_url=current_user.avatar_url,
        )
    )


@router.post("/logout")
async def logout():
    return {"status": "ok"}
