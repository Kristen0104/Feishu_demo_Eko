from __future__ import annotations

from pydantic import BaseModel, Field


class AuthContext(BaseModel):
    user_id: str
    roles: list[str] = Field(default_factory=list)


def get_auth_context() -> AuthContext:
    # Real token parsing and permission mapping will plug in here later.
    return AuthContext(user_id="stub-user", roles=["owner"])
