from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.modules.auth.schemas import FeishuOAuthIdentity, FeishuOAuthTokenResult
from app.modules.auth.repository import FeishuOAuthTokenUpsert
from app.modules.feishu.user_token_service import FeishuUserTokenService


class _FakeRepository:
    def __init__(self, token) -> None:
        self.token = token
        self.saved_tokens: list[FeishuOAuthTokenUpsert] = []

    async def get_latest_token_by_user_id(self, user_id: str):
        assert user_id == "user_123"
        return self.token

    async def save_oauth_token(self, user_id: str, token: FeishuOAuthTokenUpsert):
        assert user_id == "user_123"
        self.saved_tokens.append(token)
        return token


class _FakeProvider:
    async def refresh_access_token(self, refresh_token: str) -> FeishuOAuthTokenResult:
        assert refresh_token == "refresh-token"
        return FeishuOAuthTokenResult(
            access_token="refreshed-token",
            token_type="Bearer",
            expires_in=7200,
            refresh_token="new-refresh-token",
            refresh_expires_in=2592000,
            scope=None,
            sid=None,
            identity=FeishuOAuthIdentity(open_id="ou_123", name="测试用户"),
        )


def test_get_user_access_token_returns_cached_token_when_not_expired() -> None:
    async def run_test() -> None:
        repository = _FakeRepository(
            SimpleNamespace(
                access_token="cached-token",
                refresh_token="refresh-token",
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )
        service = FeishuUserTokenService(repository=repository, provider=_FakeProvider())

        result = await service.get_user_access_token("user_123")

        assert result == "cached-token"
        assert repository.saved_tokens == []

    asyncio.run(run_test())


def test_get_user_access_token_refreshes_expired_token() -> None:
    async def run_test() -> None:
        repository = _FakeRepository(
            SimpleNamespace(
                access_token="expired-token",
                refresh_token="refresh-token",
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        service = FeishuUserTokenService(repository=repository, provider=_FakeProvider())

        result = await service.get_user_access_token("user_123")

        assert result == "refreshed-token"
        assert len(repository.saved_tokens) == 1
        assert repository.saved_tokens[0].refresh_token == "new-refresh-token"

    asyncio.run(run_test())
