from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import FeishuAccount, FeishuOAuthToken, User
from app.modules.auth.schemas import AuthUserUpdateRequest, FeishuOAuthTokenResult


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

    async def get_user_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))

    async def create_local_user(self, *, email: str, display_name: str, password_hash: str) -> User:
        now = datetime.now(UTC)
        user = User(
            email=email,
            name=display_name,
            display_name=display_name,
            password_hash=password_hash,
            avatar_url=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(user)
        await self._session.flush()
        await self._commit()
        return user

    async def get_feishu_account_by_user_id(self, user_id: str) -> FeishuAccount | None:
        return await self._session.scalar(select(FeishuAccount).where(FeishuAccount.user_id == user_id))

    async def get_feishu_account_by_open_id(self, open_id: str) -> FeishuAccount | None:
        return await self._session.scalar(select(FeishuAccount).where(FeishuAccount.open_id == open_id))

    async def get_feishu_account_by_identity(self, *, open_id: str, union_id: str | None = None) -> FeishuAccount | None:
        conditions = [FeishuAccount.open_id == open_id]
        if union_id:
            conditions.append(FeishuAccount.union_id == union_id)
        return await self._session.scalar(select(FeishuAccount).where(or_(*conditions)))

    async def resolve_user_by_feishu_identity(self, *, open_id: str | None, union_id: str | None = None) -> User | None:
        conditions = []
        if open_id:
            conditions.append(FeishuAccount.open_id == open_id)
        if union_id:
            conditions.append(FeishuAccount.union_id == union_id)
        if not conditions:
            return None
        return await self._session.scalar(
            select(User)
            .join(FeishuAccount, FeishuAccount.user_id == User.id)
            .where(or_(*conditions))
        )

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
        await self._commit()
        return oauth_token

    async def update_user_profile(self, user: User, payload: AuthUserUpdateRequest) -> User:
        data = payload.model_dump(exclude_unset=True)
        now = datetime.now(UTC)

        if "display_name" in data and data["display_name"] is not None:
            display_name = data["display_name"].strip()
            if display_name:
                user.display_name = display_name
                user.name = display_name

        if "email" in data:
            email = self._clean_optional(data["email"])
            user.email = email.lower() if email else None

        if "name_en" in data:
            user.name_en = self._clean_optional(data["name_en"])

        scalar_fields = {
            "avatar_url": "avatar_url",
            "phone": "phone",
            "phone_ext": "phone_ext",
            "location": "location",
            "time_zone": "time_zone",
            "employee_id": "employee_id",
            "job_title": "job_title",
            "department": "department",
            "team": "team",
            "reports_to": "reports_to",
            "joined_at": "joined_at",
            "bio": "bio",
        }
        for payload_key, attr in scalar_fields.items():
            if payload_key in data:
                setattr(user, attr, self._clean_optional(data[payload_key]))

        if "languages" in data:
            languages = data["languages"] or []
            cleaned = [item.strip() for item in languages if isinstance(item, str) and item.strip()]
            user.languages = "||".join(cleaned[:10]) or None

        user.updated_at = now
        await self._session.flush()
        await self._commit()
        return user

    async def update_password_hash(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        user.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._commit()
        return user

    async def bind_feishu_identity(self, *, user: User, identity: FeishuIdentityUpsert) -> User:
        now = datetime.now(UTC)
        account = await self.get_feishu_account_by_identity(open_id=identity.open_id, union_id=identity.union_id)
        if account is not None and account.user_id != user.id:
            raise ValueError("Feishu account is already bound to another user")

        existing_for_user = await self.get_feishu_account_by_user_id(user.id)
        if existing_for_user is not None and existing_for_user.id != (account.id if account else None):
            account = existing_for_user

        if account is None:
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
            account.open_id = identity.open_id
            account.union_id = identity.union_id
            account.tenant_key = identity.tenant_key
            account.email = identity.email
            account.updated_at = now

        if not user.avatar_url and identity.avatar_url:
            user.avatar_url = identity.avatar_url
        if not user.email and identity.email:
            user.email = identity.email.lower()
        if (not user.display_name or user.display_name == user.email) and identity.name:
            user.display_name = identity.name
            user.name = identity.name
        user.updated_at = now

        await self._session.flush()
        oauth_token = identity.oauth_token()
        if oauth_token is not None:
            await self.save_oauth_token(user.id, oauth_token)
        await self._commit()
        return user

    async def upsert_feishu_identity(self, identity: FeishuIdentityUpsert) -> User:
        now = datetime.now(UTC)
        conditions = [FeishuAccount.open_id == identity.open_id]
        if identity.union_id:
            conditions.append(FeishuAccount.union_id == identity.union_id)
        account = await self._session.scalar(
            select(FeishuAccount).where(or_(*conditions))
        )

        if account is None:
            user = await self.get_user_by_email(identity.email.lower()) if identity.email else None
            if user is None:
                user = User(
                    name=identity.name,
                    display_name=identity.name,
                    email=identity.email.lower() if identity.email else None,
                    avatar_url=identity.avatar_url,
                    created_at=now,
                    updated_at=now,
                )
                self._session.add(user)
                await self._session.flush()
            else:
                if not user.avatar_url and identity.avatar_url:
                    user.avatar_url = identity.avatar_url
                user.updated_at = now
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
            user.name = identity.name
            user.display_name = identity.name
            user.email = identity.email or user.email
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
        await self._commit()
        return user

    def _clean_optional(self, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    async def _commit(self) -> None:
        commit = getattr(self._session, "commit", None)
        if commit is None:
            return
        await commit()
