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
    name_en: str | None = None
    feishu_user_id: str
    email: str | None = None
    avatar_url: str | None = None
    feishu_bound: bool = False
    union_id: str | None = None
    phone: str | None = None
    phone_ext: str | None = None
    location: str | None = None
    time_zone: str | None = None
    employee_id: str | None = None
    job_title: str | None = None
    department: str | None = None
    team: str | None = None
    reports_to: str | None = None
    joined_at: str | None = None
    bio: str | None = None
    languages: list[str] = Field(default_factory=list)


class AuthUserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500000)
    phone: str | None = Field(default=None, max_length=64)
    phone_ext: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=255)
    time_zone: str | None = Field(default=None, max_length=255)
    employee_id: str | None = Field(default=None, max_length=64)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    team: str | None = Field(default=None, max_length=255)
    reports_to: str | None = Field(default=None, max_length=255)
    joined_at: str | None = Field(default=None, max_length=64)
    bio: str | None = Field(default=None, max_length=2048)
    languages: list[str] | None = None


class AuthPasswordUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


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
