"""
认证授权 API 模块
提供飞书 OAuth 登录和用户信息获取接口（待实现）
"""
from fastapi import APIRouter, HTTPException, status
from app.schemas.schemas import FeishuLoginRequest, TokenResponse, UserInfo

router = APIRouter()


@router.post("/feishu/login", response_model=TokenResponse)
async def feishu_login(request: FeishuLoginRequest):
    # TODO: Implement Feishu OAuth code exchange
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/me", response_model=UserInfo)
async def get_current_user():
    # TODO: Implement user info retrieval
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
