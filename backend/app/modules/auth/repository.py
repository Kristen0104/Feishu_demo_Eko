from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import FeishuAccount, FeishuOAuthToken, User
from app.modules.auth.schemas import FeishuOAuthTokenResult


@dataclass(slots=True)
class FeishuOAuthTokenUpsert:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    refresh_expires_at: datetime | None
    token_type: str = "Bearer"
    scope: str | None = None

    @classmethod
    def from_oauth_result(cls, result: FeishuOAuthTokenResult) -> "FeishuOAuthTokenUpsert":
        now = datetime.now(UTC)
        refresh_expires_at = None
        if result.refresh_expires_in is not None:
            refresh_expires_at = now + timedelta(seconds=result.refresh_expires_in)
        return cls(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_at=now + timedelta(seconds=result.expires_in),
            refresh_expires_at=refresh_expires_at,
            token_type=result.token_type,
            scope=result.scope,
        )


@dataclass(slots=True)
class FeishuIdentityUpsert:
    open_id: str
    union_id: str | None
    name: str
    avatar_url: str | None
    tenant_key: str | None = None
    email: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    refresh_expires_at: datetime | None = None
    token_type: str = "Bearer"
    scope: str | None = None

    def oauth_token(self) -> FeishuOAuthTokenUpsert | None:
        if self.access_token is None or self.expires_at is None:
            return None
        return FeishuOAuthTokenUpsert(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            expires_at=self.expires_at,
            refresh_expires_at=self.refresh_expires_at,
            token_type=self.token_type,
            scope=self.scope,
        )


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self._session.scalar(select(User).where(User.id == user_id))

    async def get_feishu_account_by_user_id(self, user_id: str) -> FeishuAccount | None:
        return await self._session.scalar(select(FeishuAccount).where(FeishuAccount.user_id == user_id))

    async def get_feishu_account_by_open_id(self, open_id: str) -> FeishuAccount | None:
        return await self._session.scalar(select(FeishuAccount).where(FeishuAccount.open_id == open_id))

    async def get_latest_token_by_user_id(self, user_id: str) -> FeishuOAuthToken | None:
        return await self._session.scalar(
            select(FeishuOAuthToken)
            .where(FeishuOAuthToken.user_id == user_id)
            .order_by(FeishuOAuthToken.created_at.desc())
        )

    async def save_oauth_token(self, user_id: str, token: FeishuOAuthTokenUpsert) -> FeishuOAuthToken:
        now = datetime.now(UTC)
        oauth_token = FeishuOAuthToken(
            user_id=user_id,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            scope=token.scope,
            expires_at=token.expires_at,
            refresh_expires_at=token.refresh_expires_at,
            created_at=now,
            updated_at=now,
        )
        self._session.add(oauth_token)
        await self._session.flush()
        return oauth_token

    async def upsert_feishu_identity(self, identity: FeishuIdentityUpsert) -> User:
        now = datetime.now(UTC)
        account = await self._session.scalar(
            select(FeishuAccount).where(
                or_(FeishuAccount.open_id == identity.open_id, FeishuAccount.union_id == identity.union_id)
            )
        )

        if account is None:
            user = User(display_name=identity.name, avatar_url=identity.avatar_url, created_at=now, updated_at=now)
            self._session.add(user)
            await self._session.flush()
            account = FeishuAccount(
                user_id=user.id,
                open_id=identity.open_id,
                union_id=identity.union_id,
                tenant_key=identity.tenant_key,
                email=identity.email,
                created_at=now,
                updated_at=now,
            )
            self._session.add(account)
        else:
            user = await self.get_user_by_id(account.user_id)
            user.display_name = identity.name
            user.avatar_url = identity.avatar_url
            user.updated_at = now
            account.open_id = identity.open_id
            account.union_id = identity.union_id
            account.tenant_key = identity.tenant_key
            account.email = identity.email
            account.updated_at = now

        await self._session.flush()
        oauth_token = identity.oauth_token()
        if oauth_token is not None:
            await self.save_oauth_token(user.id, oauth_token)
        return user
