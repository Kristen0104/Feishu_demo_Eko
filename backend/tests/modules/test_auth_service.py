from __future__ import annotations

import asyncio
from collections import namedtuple

from jose import jwt

from app.config import Settings
from app.core.security import AuthContext
from app.modules.auth.schemas import FeishuCallbackRequest, FeishuLoginUrlSchema, FeishuOAuthIdentity, FeishuOAuthTokenResult
from app.modules.auth.service import AuthService


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        _ = ex
        self.values[key] = value

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


class _FakeProvider:
    def build_authorize_url(self, state: str, redirect_uri: str | None = None) -> FeishuLoginUrlSchema:
        return FeishuLoginUrlSchema(
            authorize_url=f"https://accounts.feishu.cn/open-apis/authen/v1/authorize?state={state}&redirect_uri={redirect_uri}",
            state=state,
            expires_in=600,
        )

    async def exchange_code(self, code: str, redirect_uri: str | None = None) -> FeishuOAuthTokenResult:
        assert code == "code-123"
        assert redirect_uri == "http://localhost:8000/frontend/test.html"
        return FeishuOAuthTokenResult(
            access_token="feishu-user-token",
            token_type="Bearer",
            expires_in=7200,
            refresh_token="refresh-token",
            refresh_expires_in=2592000,
            scope="contact:user.base:readonly",
            sid=None,
            identity=FeishuOAuthIdentity(
                open_id="ou_123",
                union_id="on_123",
                name="测试用户",
                avatar_url="https://example.com/avatar.png",
                tenant_key="tenant_123",
                email="tester@example.com",
            ),
        )


class _FakeRepository:
    def __init__(self) -> None:
        self.user = namedtuple("UserRecord", "id display_name avatar_url")(
            "user_123",
            "测试用户",
            "https://example.com/avatar.png",
        )
        self.account = namedtuple("AccountRecord", "open_id")("ou_123")
        self.upserts = []

    async def upsert_feishu_identity(self, payload):
        self.upserts.append(payload)
        return self.user

    async def get_feishu_account_by_user_id(self, user_id: str):
        assert user_id == "user_123"
        return self.account

    async def get_user_by_id(self, user_id: str):
        assert user_id == "user_123"
        return self.user


def test_auth_service_creates_login_url_and_callback_jwt() -> None:
    async def run_test() -> None:
        settings = Settings(
            SECRET_KEY="test-secret",
            JWT_ISSUER="test-issuer",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            FEISHU_OAUTH_REDIRECT_URI="http://localhost:8000/api/v1/auth/feishu/callback",
            FEISHU_OAUTH_STATE_TTL_SECONDS=600,
        )
        redis_client = _FakeRedis()
        repository = _FakeRepository()
        service = AuthService(
            provider=_FakeProvider(),
            repository=repository,
            redis_client=redis_client,
            settings=settings,
        )

        login_url = await service.create_feishu_login_url("http://localhost:8000/frontend/test.html")
        callback_result = await service.login_with_feishu_callback(
            FeishuCallbackRequest(
                code="code-123",
                state=login_url.state,
                redirect_uri="http://localhost:8000/frontend/test.html",
            )
        )
        current_user = await service.get_current_user(AuthContext(user_id="user_123", feishu_user_id="ou_123"))

        assert login_url.authorize_url.startswith("https://accounts.feishu.cn/open-apis/authen/v1/authorize")
        assert repository.upserts[0].open_id == "ou_123"
        assert login_url.state not in redis_client.values
        assert callback_result.user.user_id == "user_123"
        assert current_user.feishu_user_id == "ou_123"

        claims = jwt.decode(
            callback_result.access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
        assert claims["sub"] == "user_123"
        assert claims["feishu_user_id"] == "ou_123"

    asyncio.run(run_test())
