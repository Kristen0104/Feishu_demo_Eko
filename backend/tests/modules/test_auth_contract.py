from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.provider import FeishuOAuthProviderProtocol
from app.modules.auth.router import router
from app.modules.auth.schemas import AuthTokenSchema, AuthUserSchema, FeishuLoginRequest
from app.modules.auth.service import AuthService


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return TestClient(app)


def test_feishu_login_contract_returns_stub_token_and_user() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/auth/feishu/login",
        json={"code": "stub-code", "state": "stub-state"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["access_token"] == "stub-access-token"
    assert payload["data"]["user"]["feishu_user_id"] == "stub-feishu-user"


def test_current_user_contract_returns_stub_user() -> None:
    client = _build_client()

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["user_id"] == "stub-user"
    assert payload["data"]["feishu_user_id"] == "stub-feishu-user"


def test_feishu_login_rejects_malformed_payload() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/auth/feishu/login",
        json={"code": "stub-code"},
    )

    assert response.status_code == 422


def test_feishu_login_honors_auth_service_dependency_override() -> None:
    class OverrideProvider(FeishuOAuthProviderProtocol):
        def exchange_code(self, payload: FeishuLoginRequest) -> AuthTokenSchema:
            return AuthTokenSchema(
                access_token=f"override-{payload.code}",
                expires_in=600,
                user=AuthUserSchema(
                    user_id="override-user",
                    display_name="Override User",
                    feishu_user_id="override-feishu-user",
                ),
            )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: AuthService(OverrideProvider())
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/feishu/login",
        json={"code": "abc123", "state": "stub-state"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["access_token"] == "override-abc123"
    assert payload["data"]["user"]["feishu_user_id"] == "override-feishu-user"
