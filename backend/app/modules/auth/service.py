"""Authentication service helpers."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.models import User

from .token import issue_access_token


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    feishu_open_id: str | None
    name: str
    avatar_url: str | None


async def upsert_feishu_user(
    db: AsyncSession,
    feishu_open_id: str,
    name: str,
    avatar_url: str | None = None,
) -> User:
    existing = await db.execute(select(User).where(User.feishu_open_id == feishu_open_id))
    user = existing.scalar_one_or_none()
    if user is None:
        user = User(
            feishu_open_id=feishu_open_id,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
    else:
        user.name = name
        user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)
    return user


def build_authenticated_user(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        feishu_open_id=user.feishu_open_id,
        name=user.name,
        avatar_url=user.avatar_url,
    )


def issue_user_token(user: User) -> str:
    return issue_access_token(
        {
            "sub": user.id,
            "feishu_open_id": user.feishu_open_id,
            "name": user.name,
            "avatar_url": user.avatar_url,
        }
    )
