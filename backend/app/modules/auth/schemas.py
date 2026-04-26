from __future__ import annotations

from pydantic import BaseModel


class FeishuLoginRequest(BaseModel):
    code: str
    state: str


class AuthUserSchema(BaseModel):
    user_id: str
    display_name: str
    feishu_user_id: str


class AuthTokenSchema(BaseModel):
    access_token: str
    expires_in: int
    user: AuthUserSchema
