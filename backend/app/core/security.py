from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from app.config import Settings, get_settings


class AuthContext(BaseModel):
    user_id: str
    feishu_user_id: str | None = None
    token_id: str | None = None
    roles: list[str] = Field(default_factory=list)


_bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(
    *,
    user_id: str,
    feishu_user_id: str | None = None,
    roles: list[str] | None = None,
    token_id: str | None = None,
    settings: Settings | None = None,
) -> str:
    app_settings = settings or get_settings()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    resolved_token_id = token_id or uuid4().hex
    payload: dict[str, Any] = {
        "sub": user_id,
        "jti": resolved_token_id,
        "roles": roles or [],
        "iss": app_settings.JWT_ISSUER,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if feishu_user_id:
        payload["feishu_user_id"] = feishu_user_id
    return jwt.encode(payload, app_settings.SECRET_KEY, algorithm=app_settings.ALGORITHM)


def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Bearer token missing subject")
    return AuthContext(
        user_id=user_id,
        feishu_user_id=payload.get("feishu_user_id"),
        token_id=payload.get("jti"),
        roles=list(payload.get("roles", [])),
    )
