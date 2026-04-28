from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.config import Settings, get_settings
from app.core.security import AuthContext
from app.modules.auth.provider import FeishuOAuthProviderProtocol
from app.modules.auth.repository import AuthRepository, FeishuIdentityUpsert
from app.modules.auth.schemas import (
    AuthTokenSchema,
    AuthUserSchema,
    FeishuCallbackRequest,
    FeishuLoginRequest,
    FeishuLoginUrlSchema,
)


class AuthService:
    def __init__(
        self,
        provider: FeishuOAuthProviderProtocol,
        repository: AuthRepository,
        redis_client,
        settings: Settings | None = None,
        token_factory=None,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._redis = redis_client
        self._settings = settings or get_settings()
        self._token_factory = token_factory

    async def create_feishu_login_url(self, redirect_uri: str | None = None) -> FeishuLoginUrlSchema:
        state = secrets.token_urlsafe(24)
        resolved_redirect_uri = redirect_uri or self._settings.FEISHU_OAUTH_REDIRECT_URI
        await self._redis.set(
            self._state_key(state),
            resolved_redirect_uri,
            ex=self._settings.FEISHU_OAUTH_STATE_TTL_SECONDS,
        )
        return self._provider.build_authorize_url(state=state, redirect_uri=resolved_redirect_uri)

    async def login_with_feishu(self, payload: FeishuLoginRequest) -> AuthTokenSchema:
        return await self.login_with_feishu_callback(
            FeishuCallbackRequest(
                code=payload.code,
                state=payload.state,
                redirect_uri=payload.redirect_uri,
            )
        )

    async def login_with_feishu_callback(self, payload: FeishuCallbackRequest) -> AuthTokenSchema:
        redirect_uri = await self._consume_state(payload.state)
        oauth_result = await self._provider.exchange_code(payload.code, payload.redirect_uri or redirect_uri)
        user = await self._repository.upsert_feishu_identity(
            FeishuIdentityUpsert(
                open_id=oauth_result.identity.open_id,
                union_id=oauth_result.identity.union_id,
                name=oauth_result.identity.name,
                avatar_url=oauth_result.identity.avatar_url,
                tenant_key=oauth_result.identity.tenant_key,
                email=oauth_result.identity.email,
                access_token=oauth_result.access_token,
                refresh_token=oauth_result.refresh_token,
                expires_at=self._expires_at(oauth_result.expires_in),
                refresh_expires_at=self._expires_at(oauth_result.refresh_expires_in),
                token_type=oauth_result.token_type,
                scope=oauth_result.scope,
            )
        )
        account = await self._repository.get_feishu_account_by_user_id(user.id)
        return AuthTokenSchema(
            access_token=self._build_access_token(user.id, account.open_id if account else oauth_result.identity.open_id),
            token_type="Bearer",
            expires_in=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=AuthUserSchema(
                user_id=user.id,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                feishu_user_id=account.open_id if account else oauth_result.identity.open_id,
            ),
        )

    async def get_current_user(self, auth_context: AuthContext) -> AuthUserSchema:
        user = await self._repository.get_user_by_id(auth_context.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Authenticated user was not found")
        account = await self._repository.get_feishu_account_by_user_id(user.id)
        return AuthUserSchema(
            user_id=user.id,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            feishu_user_id=(account.open_id if account else auth_context.feishu_user_id) or "",
        )

    async def _consume_state(self, state: str) -> str:
        key = self._state_key(state)
        redirect_uri = await self._redis.get(key)
        if redirect_uri is None:
            raise HTTPException(status_code=400, detail="Feishu OAuth state is invalid or expired")
        await self._redis.delete(key)
        return redirect_uri

    def _build_access_token(self, user_id: str, feishu_user_id: str | None) -> str:
        if self._token_factory is not None:
            return self._token_factory(user_id=user_id, feishu_user_id=feishu_user_id, roles=["member"])
        from app.core.security import create_access_token

        return create_access_token(
            user_id=user_id,
            feishu_user_id=feishu_user_id,
            roles=["member"],
            settings=self._settings,
        )

    def _state_key(self, state: str) -> str:
        return f"feishu:oauth:state:{state}"

    def _expires_at(self, expires_in: int | None) -> datetime | None:
        if expires_in is None:
            return None
        return datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=expires_in)
