from __future__ import annotations

from typing import Protocol

from app.modules.auth.schemas import AuthTokenSchema, AuthUserSchema, FeishuLoginRequest


class FeishuOAuthProviderProtocol(Protocol):
    def exchange_code(self, payload: FeishuLoginRequest) -> AuthTokenSchema: ...


class FeishuOAuthProvider:
    def exchange_code(self, payload: FeishuLoginRequest) -> AuthTokenSchema:
        _ = payload
        return AuthTokenSchema(
            access_token="stub-access-token",
            expires_in=3600,
            user=AuthUserSchema(
                user_id="stub-user",
                display_name="Stub User",
                feishu_user_id="stub-feishu-user",
            ),
        )
