from __future__ import annotations

from app.core.security import AuthContext
from app.modules.auth.provider import FeishuOAuthProviderProtocol
from app.modules.auth.schemas import AuthTokenSchema, AuthUserSchema, FeishuLoginRequest


class AuthService:
    def __init__(self, provider: FeishuOAuthProviderProtocol) -> None:
        self._provider = provider

    def login_with_feishu(self, payload: FeishuLoginRequest) -> AuthTokenSchema:
        return self._provider.exchange_code(payload)

    def get_current_user(self, auth_context: AuthContext) -> AuthUserSchema:
        return AuthUserSchema(
            user_id=auth_context.user_id,
            display_name="Stub User",
            feishu_user_id="stub-feishu-user",
        )
