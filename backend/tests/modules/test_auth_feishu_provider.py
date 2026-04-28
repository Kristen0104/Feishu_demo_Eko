from __future__ import annotations

import asyncio

import httpx

from app.config import Settings
from app.modules.auth.provider import FeishuOAuthProvider


def test_build_authorize_url_includes_state_and_redirect_uri() -> None:
    provider = FeishuOAuthProvider(
        settings=Settings(
            FEISHU_APP_ID="cli_app_id",
            FEISHU_APP_SECRET="cli_app_secret",
            FEISHU_OAUTH_REDIRECT_URI="http://localhost:8000/api/v1/auth/feishu/callback",
        )
    )

    result = provider.build_authorize_url(
        state="state-123",
        redirect_uri="http://localhost:8000/frontend/test.html",
    )

    assert result.state == "state-123"
    assert result.authorize_url.startswith("https://accounts.feishu.cn/open-apis/authen/v1/authorize")
    assert "client_id=cli_app_id" in result.authorize_url
    assert "state=state-123" in result.authorize_url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Ffrontend%2Ftest.html" in result.authorize_url


def test_exchange_code_uses_oauth_v2_token_and_maps_identity() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/open-apis/authen/v2/oauth/token":
            assert request.content.decode() == (
                '{"grant_type":"authorization_code","code":"code-123",'
                '"client_id":"cli_app_id","client_secret":"cli_app_secret",'
                '"redirect_uri":"http://127.0.0.1:8010/frontend/test.html"}'
            )
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": "user-token",
                    "token_type": "Bearer",
                    "expires_in": 7200,
                    "refresh_token": "refresh-token",
                    "refresh_token_expires_in": 2592000,
                    "scope": "auth:user.id:read offline_access",
                },
            )
        if request.url.path == "/open-apis/authen/v1/user_info":
            assert request.headers["Authorization"] == "Bearer user-token"
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "name": "测试用户",
                        "open_id": "ou_123",
                        "union_id": "on_123",
                        "tenant_key": "tenant_123",
                        "avatar_url": "https://example.com/avatar.png",
                        "email": "tester@example.com",
                    },
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://open.feishu.cn",
        ) as client:
            provider = FeishuOAuthProvider(
                settings=Settings(FEISHU_APP_ID="cli_app_id", FEISHU_APP_SECRET="cli_app_secret"),
                client=client,
            )
            result = await provider.exchange_code("code-123", "http://127.0.0.1:8010/frontend/test.html")

        assert result.access_token == "user-token"
        assert result.identity.open_id == "ou_123"
        assert result.identity.name == "测试用户"
        assert result.refresh_expires_in == 2592000
        assert len(requests) == 2

    asyncio.run(run_test())


def test_refresh_access_token_uses_refresh_grant() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/open-apis/authen/v2/oauth/token":
            assert request.content.decode() == (
                '{"grant_type":"refresh_token","refresh_token":"refresh-token",'
                '"client_id":"cli_app_id","client_secret":"cli_app_secret"}'
            )
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": "new-user-token",
                    "token_type": "Bearer",
                    "expires_in": 7200,
                    "refresh_token": "new-refresh-token",
                    "refresh_token_expires_in": 2592000,
                },
            )
        if request.url.path == "/open-apis/authen/v1/user_info":
            assert request.headers["Authorization"] == "Bearer new-user-token"
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "name": "测试用户",
                        "open_id": "ou_123",
                    },
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    async def run_test() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://open.feishu.cn",
        ) as client:
            provider = FeishuOAuthProvider(
                settings=Settings(FEISHU_APP_ID="cli_app_id", FEISHU_APP_SECRET="cli_app_secret"),
                client=client,
            )
            result = await provider.refresh_access_token("refresh-token")

        assert result.access_token == "new-user-token"
        assert result.refresh_token == "new-refresh-token"
        assert result.identity.open_id == "ou_123"

    asyncio.run(run_test())


def test_default_http_client_disables_environment_proxy(monkeypatch) -> None:
    captured_kwargs = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def request(self, method: str, path: str, **kwargs):
            return httpx.Response(200, json={"code": 0, "msg": "success", "data": {}}, request=httpx.Request(method, path))

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr("app.modules.auth.provider.httpx.AsyncClient", FakeAsyncClient)

    async def run_test() -> None:
        provider = FeishuOAuthProvider(settings=Settings())
        await provider._request("GET", "/open-apis/authen/v1/user_info")

    asyncio.run(run_test())

    assert captured_kwargs["trust_env"] is False
