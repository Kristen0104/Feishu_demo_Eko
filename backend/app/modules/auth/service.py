from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.config import Settings, get_settings
from app.core.security import AuthContext, create_access_token
from app.modules.auth.passwords import hash_password, verify_password
from app.modules.auth.provider import FeishuOAuthProviderProtocol
from app.modules.auth.repository import AuthRepository, FeishuIdentityUpsert
from app.modules.auth.schemas import (
    AuthLoginRequest,
    AuthPasswordUpdateRequest,
    AuthRegisterRequest,
    AuthTokenSchema,
    AuthUserUpdateRequest,
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

    async def register_with_password(self, payload: AuthRegisterRequest) -> AuthTokenSchema:
        email = self._normalize_email(payload.email)
        if await self._repository.get_user_by_email(email) is not None:
            raise HTTPException(status_code=409, detail="Email already registered")
        user = await self._repository.create_local_user(
            email=email,
            display_name=payload.display_name.strip(),
            password_hash=hash_password(payload.password),
        )
        return await self._issue_token_for_user(user)

    async def login_with_password(self, payload: AuthLoginRequest) -> AuthTokenSchema:
        email = self._normalize_email(payload.email)
        user = await self._repository.get_user_by_email(email)
        if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return await self._issue_token_for_user(user)

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
        return await self._issue_token_for_user(user, feishu_user_id=account.open_id if account else oauth_result.identity.open_id)

    async def bind_feishu_callback(self, auth_context: AuthContext, payload: FeishuCallbackRequest) -> AuthUserSchema:
        if auth_context.token_id:
            await self._ensure_session_active(auth_context.token_id, auth_context.user_id)

        redirect_uri = await self._consume_state(payload.state)
        oauth_result = await self._provider.exchange_code(payload.code, payload.redirect_uri or redirect_uri)
        user = await self._repository.get_user_by_id(auth_context.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Authenticated user was not found")

        try:
            await self._repository.bind_feishu_identity(
                user=user,
                identity=FeishuIdentityUpsert(
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
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return await self.get_current_user(auth_context)

    async def get_current_user(self, auth_context: AuthContext) -> AuthUserSchema:
        if auth_context.token_id:
            await self._ensure_session_active(auth_context.token_id, auth_context.user_id)

        user = await self._repository.get_user_by_id(auth_context.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Authenticated user was not found")
        account = await self._repository.get_feishu_account_by_user_id(user.id)
        return AuthUserSchema(
            user_id=user.id,
            display_name=user.display_name,
            name_en=getattr(user, "name_en", None),
            avatar_url=user.avatar_url,
            feishu_user_id=(account.open_id if account else auth_context.feishu_user_id) or "",
            feishu_bound=account is not None,
            union_id=account.union_id if account else None,
            email=getattr(user, "email", None),
            phone=getattr(user, "phone", None),
            phone_ext=getattr(user, "phone_ext", None),
            location=getattr(user, "location", None),
            time_zone=getattr(user, "time_zone", None),
            employee_id=getattr(user, "employee_id", None),
            job_title=getattr(user, "job_title", None),
            department=getattr(user, "department", None),
            team=getattr(user, "team", None),
            reports_to=getattr(user, "reports_to", None),
            joined_at=getattr(user, "joined_at", None),
            bio=getattr(user, "bio", None),
            languages=self._parse_languages(getattr(user, "languages", None)),
        )

    async def update_current_user(self, auth_context: AuthContext, payload: AuthUserUpdateRequest) -> AuthUserSchema:
        if auth_context.token_id:
            await self._ensure_session_active(auth_context.token_id, auth_context.user_id)

        if payload.email:
            email = self._normalize_email(payload.email)
            existing = await self._repository.get_user_by_email(email)
            if existing is not None and existing.id != auth_context.user_id:
                raise HTTPException(status_code=409, detail="Email already registered")

        user = await self._repository.get_user_by_id(auth_context.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Authenticated user was not found")
        await self._repository.update_user_profile(user, payload)
        return await self.get_current_user(auth_context)

    async def update_current_password(self, auth_context: AuthContext, payload: AuthPasswordUpdateRequest) -> AuthUserSchema:
        if auth_context.token_id:
            await self._ensure_session_active(auth_context.token_id, auth_context.user_id)

        user = await self._repository.get_user_by_id(auth_context.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Authenticated user was not found")
        if not user.password_hash:
            raise HTTPException(status_code=400, detail="Current account does not have a password")
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        await self._repository.update_password_hash(user, hash_password(payload.new_password))
        return await self.get_current_user(auth_context)

    async def _issue_token_for_user(self, user, feishu_user_id: str | None = None) -> AuthTokenSchema:
        token_id = secrets.token_urlsafe(24)
        access_token = self._build_access_token(user.id, feishu_user_id, token_id=token_id)
        await self._store_session(
            token_id=token_id,
            user_id=user.id,
            feishu_user_id=feishu_user_id,
            email=getattr(user, "email", None),
        )
        return AuthTokenSchema(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=AuthUserSchema(
                user_id=user.id,
                display_name=user.display_name,
                name_en=getattr(user, "name_en", None),
                avatar_url=user.avatar_url,
                feishu_user_id=feishu_user_id or "",
                feishu_bound=bool(feishu_user_id),
                email=getattr(user, "email", None),
                phone=getattr(user, "phone", None),
                phone_ext=getattr(user, "phone_ext", None),
                location=getattr(user, "location", None),
                time_zone=getattr(user, "time_zone", None),
                employee_id=getattr(user, "employee_id", None),
                job_title=getattr(user, "job_title", None),
                department=getattr(user, "department", None),
                team=getattr(user, "team", None),
                reports_to=getattr(user, "reports_to", None),
                joined_at=getattr(user, "joined_at", None),
                bio=getattr(user, "bio", None),
                languages=self._parse_languages(getattr(user, "languages", None)),
            ),
        )

    async def _ensure_session_active(self, token_id: str, user_id: str) -> None:
        session = await self._redis.get(self._session_key(token_id))
        if session is None:
            raise HTTPException(status_code=401, detail="Session expired")
        try:
            payload = json.loads(session)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=401, detail="Session expired") from exc
        if payload.get("user_id") != user_id:
            raise HTTPException(status_code=401, detail="Session expired")

    async def _store_session(
        self,
        *,
        token_id: str,
        user_id: str,
        feishu_user_id: str | None,
        email: str | None,
    ) -> None:
        session = {
            "user_id": user_id,
            "feishu_user_id": feishu_user_id,
            "email": email,
            "roles": ["member"],
        }
        await self._redis.set(
            self._session_key(token_id),
            json.dumps(session, ensure_ascii=False),
            ex=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def _consume_state(self, state: str) -> str:
        key = self._state_key(state)
        redirect_uri = await self._redis.get(key)
        if redirect_uri is None:
            raise HTTPException(status_code=400, detail="Feishu OAuth state is invalid or expired")
        await self._redis.delete(key)
        return redirect_uri

    def _build_access_token(self, user_id: str, feishu_user_id: str | None, *, token_id: str | None = None) -> str:
        if self._token_factory is not None:
            return self._token_factory(user_id=user_id, feishu_user_id=feishu_user_id, roles=["member"], token_id=token_id)

        return create_access_token(
            user_id=user_id,
            feishu_user_id=feishu_user_id,
            roles=["member"],
            token_id=token_id,
            settings=self._settings,
        )

    def _state_key(self, state: str) -> str:
        return f"feishu:oauth:state:{state}"

    def _session_key(self, token_id: str) -> str:
        return f"auth:session:{token_id}"

    def _expires_at(self, expires_in: int | None) -> datetime | None:
        if expires_in is None:
            return None
        return datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=expires_in)

    def _normalize_email(self, email: str) -> str:
        normalized = email.strip().lower()
        if not normalized or "@" not in normalized:
            raise HTTPException(status_code=400, detail="Invalid email")
        return normalized

    def _parse_languages(self, raw: str | None) -> list[str]:
        if not raw:
            return []
        return [item for item in raw.split("||") if item]
