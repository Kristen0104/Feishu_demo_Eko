from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from jose import jwt

from app.config import Settings
from app.core.security import AuthContext
from app.modules.auth.models import User
from app.modules.auth.schemas import AuthLoginRequest, AuthRegisterRequest
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
    def build_authorize_url(self, state: str, redirect_uri: str | None = None):  # pragma: no cover - not used
        raise AssertionError("Feishu provider should not be used in local auth tests")

    async def exchange_code(self, code: str, redirect_uri: str | None = None):  # pragma: no cover - not used
        raise AssertionError("Feishu provider should not be used in local auth tests")

    async def refresh_access_token(self, refresh_token: str):  # pragma: no cover - not used
        raise AssertionError("Feishu provider should not be used in local auth tests")


class _LocalAuthRepository:
    def __init__(self) -> None:
        self.users_by_email: dict[str, User] = {}
        self.users_by_id: dict[str, User] = {}

    async def get_user_by_email(self, email: str) -> User | None:
        return self.users_by_email.get(email)

    async def get_user_by_id(self, user_id: str) -> User | None:
        return self.users_by_id.get(user_id)

    async def create_local_user(self, *, email: str, display_name: str, password_hash: str) -> User:
        now = datetime.now(UTC)
        user = User(
            id=f"user_{len(self.users_by_id) + 1}",
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            avatar_url=None,
            created_at=now,
            updated_at=now,
        )
        self.users_by_email[email] = user
        self.users_by_id[user.id] = user
        return user

    async def get_feishu_account_by_user_id(self, user_id: str):
        _ = user_id
        return None


def test_register_issues_jwt_and_persists_redis_session() -> None:
    async def run_test() -> None:
        settings = Settings(SECRET_KEY="test-secret", JWT_ISSUER="test-issuer", ACCESS_TOKEN_EXPIRE_MINUTES=30)
        redis_client = _FakeRedis()
        repository = _LocalAuthRepository()
        service = AuthService(provider=_FakeProvider(), repository=repository, redis_client=redis_client, settings=settings)

        result = await service.register_with_password(
            AuthRegisterRequest(
                email="alice@example.com",
                password="Password123",
                display_name="Alice",
            )
        )

        claims = jwt.decode(
            result.access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )

        assert result.user.email == "alice@example.com"
        assert claims["sub"] == result.user.user_id
        assert claims["jti"]
        assert redis_client.values[f"auth:session:{claims['jti']}"] != ""

    asyncio.run(run_test())


def test_login_rejects_wrong_password() -> None:
    async def run_test() -> None:
        settings = Settings(SECRET_KEY="test-secret", JWT_ISSUER="test-issuer", ACCESS_TOKEN_EXPIRE_MINUTES=30)
        redis_client = _FakeRedis()
        repository = _LocalAuthRepository()
        service = AuthService(provider=_FakeProvider(), repository=repository, redis_client=redis_client, settings=settings)
        await service.register_with_password(
            AuthRegisterRequest(
                email="alice@example.com",
                password="Password123",
                display_name="Alice",
            )
        )

        try:
            await service.login_with_password(
                AuthLoginRequest(
                    email="alice@example.com",
                    password="wrong-password",
                )
            )
        except Exception as exc:  # noqa: BLE001
            assert getattr(exc, "status_code", None) == 401
        else:  # pragma: no cover - defensive
            raise AssertionError("login should have failed")

    asyncio.run(run_test())


def test_current_user_requires_active_redis_session_for_jwt() -> None:
    async def run_test() -> None:
        settings = Settings(SECRET_KEY="test-secret", JWT_ISSUER="test-issuer", ACCESS_TOKEN_EXPIRE_MINUTES=30)
        redis_client = _FakeRedis()
        repository = _LocalAuthRepository()
        service = AuthService(provider=_FakeProvider(), repository=repository, redis_client=redis_client, settings=settings)

        result = await service.register_with_password(
            AuthRegisterRequest(
                email="alice@example.com",
                password="Password123",
                display_name="Alice",
            )
        )
        claims = jwt.decode(
            result.access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
        session_key = f"auth:session:{claims['jti']}"
        assert await redis_client.get(session_key) is not None

        current_user = await service.get_current_user(
            AuthContext(
                user_id=result.user.user_id,
                token_id=claims["jti"],
            )
        )
        assert current_user.email == "alice@example.com"

        await redis_client.delete(session_key)

        try:
            await service.get_current_user(
                AuthContext(
                    user_id=result.user.user_id,
                    token_id=claims["jti"],
                )
            )
        except Exception as exc:  # noqa: BLE001
            assert getattr(exc, "status_code", None) == 401
        else:  # pragma: no cover - defensive
            raise AssertionError("session validation should have failed")

    asyncio.run(run_test())
