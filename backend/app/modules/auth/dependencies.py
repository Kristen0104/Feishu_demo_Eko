from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.modules.auth.provider import FeishuOAuthProvider
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService


def get_auth_provider(settings: Annotated[Settings, Depends(get_settings)]) -> FeishuOAuthProvider:
    return FeishuOAuthProvider(settings=settings)


def get_auth_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthRepository:
    return AuthRepository(db)


async def require_redis_client(redis_client: Annotated[Redis | None, Depends(get_redis)]) -> Redis:
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis is not initialized for Feishu OAuth state storage")
    return redis_client


def get_auth_service(
    provider: Annotated[FeishuOAuthProvider, Depends(get_auth_provider)],
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    redis_client: Annotated[Redis, Depends(require_redis_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(
        provider=provider,
        repository=repository,
        redis_client=redis_client,
        settings=settings,
    )
