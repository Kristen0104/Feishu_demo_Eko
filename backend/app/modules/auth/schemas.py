from __future__ import annotations

from pydantic import BaseModel, Field


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthRegisterRequest(BaseModel):
    display_name: str
    email: str
    password: str


class FeishuLoginRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str | None = None


class FeishuCallbackRequest(FeishuLoginRequest):
    pass


class FeishuLoginUrlSchema(BaseModel):
    authorize_url: str
    state: str
    expires_in: int


class FeishuOAuthIdentity(BaseModel):
    open_id: str
    name: str
    union_id: str | None = None
    avatar_url: str | None = None
    tenant_key: str | None = None
    email: str | None = None


class AuthUserSchema(BaseModel):
    user_id: str
    display_name: str
    feishu_user_id: str
    email: str | None = None
    avatar_url: str | None = None


class FeishuOAuthTokenResult(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    refresh_expires_in: int | None = None
    scope: str | None = None
    sid: str | None = None
    identity: FeishuOAuthIdentity


class AuthTokenSchema(BaseModel):
    access_token: str
    token_type: str = Field(default="Bearer")
    expires_in: int
    user: AuthUserSchema
