from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from pydantic import BaseModel

from app.modules.auth.provider import FeishuOAuthProviderProtocol
from app.modules.auth.repository import AuthRepository, FeishuOAuthTokenUpsert


class FeishuReauthRequired(RuntimeError):
    """Raised when the bound Feishu account must be authorized again."""


class FeishuBoundIdentity(BaseModel):
    user_id: str
    feishu_open_id: str | None = None
    feishu_union_id: str | None = None
    feishu_user_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    identity_label: str | None = None


class FeishuIdentityService:
    def __init__(
        self,
        repository: AuthRepository,
        provider: FeishuOAuthProviderProtocol,
        *,
        refresh_skew_seconds: int = 60,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._refresh_skew = timedelta(seconds=refresh_skew_seconds)

    async def get_bound_identity(self, user_id: str) -> FeishuBoundIdentity | None:
        account = await self._repository.get_feishu_account_by_user_id(user_id)
        if account is None:
            return None

        user = await self._repository.get_user_by_id(user_id)
        token = await self._repository.get_latest_token_by_user_id(user_id)
        access_token = None
        refresh_token = None
        expires_at = None

        if token is not None:
            refresh_token = token.refresh_token
            expires_at = self._ensure_aware(token.expires_at)
            if expires_at - self._refresh_skew > datetime.now(UTC):
                access_token = token.access_token
            elif token.refresh_token:
                try:
                    refreshed = await self._provider.refresh_access_token(token.refresh_token)
                except HTTPException as exc:
                    raise FeishuReauthRequired("请重新绑定飞书账号") from exc
                except Exception as exc:  # noqa: BLE001
                    raise FeishuReauthRequired("请重新绑定飞书账号") from exc
                refreshed_record = FeishuOAuthTokenUpsert.from_oauth_result(refreshed)
                await self._repository.save_oauth_token(user_id, refreshed_record)
                access_token = refreshed_record.access_token
                refresh_token = refreshed_record.refresh_token
                expires_at = refreshed_record.expires_at
            else:
                raise FeishuReauthRequired("请重新绑定飞书账号")

        label = None
        if user is not None:
            label = user.display_name or user.name or user.email
        label = label or account.email or account.open_id

        return FeishuBoundIdentity(
            user_id=user_id,
            feishu_open_id=account.open_id,
            feishu_union_id=account.union_id,
            feishu_user_id=None,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            identity_label=label,
        )

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
