from __future__ import annotations

from app.modules.auth.provider import FeishuOAuthProvider
from app.modules.auth.service import AuthService


def get_auth_service() -> AuthService:
    return AuthService(FeishuOAuthProvider())
