from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.modules.auth.provider import FeishuOAuthProviderProtocol
from app.modules.auth.repository import AuthRepository, FeishuOAuthTokenUpsert


class FeishuUserTokenService:
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

    async def get_user_access_token(self, user_id: str) -> str:
        latest_token = await self._repository.get_latest_token_by_user_id(user_id)
        if latest_token is None:
            raise HTTPException(status_code=404, detail="No Feishu OAuth token found for user")

        now = datetime.now(UTC)
        if latest_token.expires_at - self._refresh_skew > now:
            return latest_token.access_token

        if not latest_token.refresh_token:
            raise HTTPException(status_code=401, detail="Feishu OAuth token expired and cannot be refreshed")

        refreshed = await self._provider.refresh_access_token(latest_token.refresh_token)
        token_record = FeishuOAuthTokenUpsert.from_oauth_result(refreshed)
        await self._repository.save_oauth_token(user_id, token_record)
        return refreshed.access_token
