from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


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
