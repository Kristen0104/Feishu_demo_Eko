from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeamInviteRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local_part, separator, domain = normalized.partition("@")
        if not separator or not local_part or "." not in domain:
            raise ValueError("Invalid email format")
        return normalized


class TeamMemberSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str | None
    role: str
    status: str
    avatar_url: str | None
    is_current_user: bool
    is_registered_user: bool
    invited_by_name: str | None
    created_at: datetime


class SessionInviteRequest(BaseModel):
    member_id: str | None = None
    email: str | None = None

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        local_part, separator, domain = normalized.partition("@")
        if not separator or not local_part or "." not in domain:
            raise ValueError("Invalid email format")
        return normalized


class SessionInviteActionRequest(BaseModel):
    action: str = Field(pattern="^(accepted|declined|dismissed)$")


class SessionCollaborationInviteSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    session_title: str
    inviter_user_id: str
    inviter_name: str
    invitee_user_id: str | None
    invitee_email: str
    invitee_name: str | None
    status: str
    is_expired: bool
    created_at: datetime
    expires_at: datetime
    responded_at: datetime | None
