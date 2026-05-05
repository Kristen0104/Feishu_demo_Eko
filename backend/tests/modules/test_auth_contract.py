from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import AuthContext, create_access_token
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.router import router
from app.modules.auth.schemas import (
    AuthTokenSchema,
    AuthUserSchema,
    AuthLoginRequest,
    AuthRegisterRequest,
    FeishuCallbackRequest,
    FeishuLoginRequest,
    FeishuLoginUrlSchema,
)


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return TestClient(app)


class _OverrideAuthService:
    async def register_with_password(self, payload: AuthRegisterRequest) -> AuthTokenSchema:
        return AuthTokenSchema(
            access_token=f"register-{payload.email}",
            token_type="Bearer",
            expires_in=600,
            user=AuthUserSchema(
                user_id="register-user",
                display_name=payload.display_name,
                avatar_url=None,
                feishu_user_id="",
                email=payload.email,
            ),
        )

    async def login_with_password(self, payload: AuthLoginRequest) -> AuthTokenSchema:
        return AuthTokenSchema(
            access_token=f"login-{payload.email}",
            token_type="Bearer",
            expires_in=600,
            user=AuthUserSchema(
                user_id="login-user",
                display_name="Login User",
                avatar_url=None,
                feishu_user_id="",
                email=payload.email,
            ),
        )

    async def create_feishu_login_url(self, redirect_uri: str | None = None) -> FeishuLoginUrlSchema:
        return FeishuLoginUrlSchema(
            authorize_url=f"https://accounts.feishu.cn/open-apis/authen/v1/authorize?redirect_uri={redirect_uri}",
            state="state-123",
            expires_in=600,
        )

    async def login_with_feishu(self, payload: FeishuLoginRequest) -> AuthTokenSchema:
        return AuthTokenSchema(
            access_token=f"override-{payload.code}",
            token_type="Bearer",
            expires_in=600,
            user=AuthUserSchema(
                user_id="override-user",
                display_name="Override User",
                avatar_url="https://example.com/avatar.png",
                feishu_user_id="override-open-id",
            ),
        )

    async def login_with_feishu_callback(self, payload: FeishuCallbackRequest) -> AuthTokenSchema:
        return await self.login_with_feishu(FeishuLoginRequest(**payload.model_dump()))

    async def get_current_user(self, auth_context: AuthContext) -> AuthUserSchema:
        return AuthUserSchema(
            user_id=auth_context.user_id,
            display_name="Override User",
            avatar_url="https://example.com/avatar.png",
            feishu_user_id=auth_context.feishu_user_id or "override-open-id",
        )


def test_feishu_login_url_contract_returns_authorize_url_and_state() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)

    response = client.get(
        "/api/v1/auth/feishu/login-url",
        params={"redirect_uri": "http://localhost:8000/frontend/test.html"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["state"] == "state-123"
    assert payload["authorize_url"].startswith("https://accounts.feishu.cn/open-apis/authen/v1/authorize")


def test_register_contract_returns_token_and_user() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "Password123", "display_name": "Alice"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["access_token"] == "register-alice@example.com"
    assert payload["user"]["email"] == "alice@example.com"


def test_login_contract_returns_token_and_user() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "Password123"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["access_token"] == "login-alice@example.com"
    assert payload["user"]["email"] == "alice@example.com"


def test_feishu_login_contract_returns_overridden_token_and_user() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/feishu/login",
        json={"code": "abc123", "state": "state-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["access_token"] == "override-abc123"
    assert payload["data"]["user"]["feishu_user_id"] == "override-open-id"


def test_feishu_callback_requires_code_and_state() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)

    response = client.get("/api/v1/auth/feishu/callback")

    assert response.status_code == 422


def test_current_user_contract_returns_override_user() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)
    access_token = create_access_token(
        user_id="jwt-user",
        feishu_user_id="jwt-open-id",
        roles=["member"],
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["user_id"] == "jwt-user"
    assert payload["data"]["feishu_user_id"] == "jwt-open-id"


def test_feishu_login_rejects_malformed_payload() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/feishu/login",
        json={"code": "stub-code"},
    )

    assert response.status_code == 422


def test_feishu_login_honors_auth_service_dependency_override() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: _OverrideAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/feishu/login",
        json={"code": "abc123", "state": "stub-state"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["access_token"] == "override-abc123"
    assert payload["data"]["user"]["feishu_user_id"] == "override-open-id"
