from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.config import Settings, get_settings
from app.modules.auth.schemas import FeishuLoginUrlSchema, FeishuOAuthIdentity, FeishuOAuthTokenResult


class FeishuOAuthProviderProtocol(Protocol):
    def build_authorize_url(self, state: str, redirect_uri: str | None = None) -> FeishuLoginUrlSchema: ...
    async def exchange_code(self, code: str, redirect_uri: str | None = None) -> FeishuOAuthTokenResult: ...
    async def refresh_access_token(self, refresh_token: str) -> FeishuOAuthTokenResult: ...


class FeishuOAuthProvider:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client

    def build_authorize_url(self, state: str, redirect_uri: str | None = None) -> FeishuLoginUrlSchema:
        resolved_redirect_uri = redirect_uri or self._settings.FEISHU_OAUTH_REDIRECT_URI
        authorize_url = (
            f"{self._settings.FEISHU_AUTH_BASE_URL}/open-apis/authen/v1/authorize?"
            f"{urlencode({'client_id': self._settings.FEISHU_APP_ID, 'redirect_uri': resolved_redirect_uri, 'scope': self._settings.FEISHU_OAUTH_SCOPE, 'state': state, 'response_type': 'code'})}"
        )
        return FeishuLoginUrlSchema(
            authorize_url=authorize_url,
            state=state,
            expires_in=self._settings.FEISHU_OAUTH_STATE_TTL_SECONDS,
        )

    async def exchange_code(self, code: str, redirect_uri: str | None = None) -> FeishuOAuthTokenResult:
        resolved_redirect_uri = redirect_uri or self._settings.FEISHU_OAUTH_REDIRECT_URI
        return await self._request_user_token(
            payload={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self._settings.FEISHU_APP_ID,
                "client_secret": self._settings.FEISHU_APP_SECRET,
                "redirect_uri": resolved_redirect_uri,
            },
        )

    async def refresh_access_token(self, refresh_token: str) -> FeishuOAuthTokenResult:
        return await self._request_user_token(
            payload={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._settings.FEISHU_APP_ID,
                "client_secret": self._settings.FEISHU_APP_SECRET,
            },
        )

    async def _request_user_token(self, *, payload: dict[str, Any]) -> FeishuOAuthTokenResult:
        response = await self._request(
            "POST",
            "/open-apis/authen/v2/oauth/token",
            json=payload,
        )
        data = response.get("data", response)
        user_info = await self._get_user_info(data["access_token"])
        return FeishuOAuthTokenResult(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data["expires_in"],
            refresh_token=data.get("refresh_token"),
            refresh_expires_in=data.get("refresh_token_expires_in") or data.get("refresh_expires_in"),
            scope=data.get("scope"),
            sid=data.get("sid"),
            identity=FeishuOAuthIdentity(
                open_id=user_info["open_id"],
                name=user_info.get("name") or user_info.get("en_name") or user_info["open_id"],
                union_id=user_info.get("union_id"),
                avatar_url=user_info.get("avatar_url"),
                tenant_key=user_info.get("tenant_key"),
                email=user_info.get("email") or user_info.get("enterprise_email"),
            ),
        )

    async def _get_user_info(self, access_token: str) -> dict[str, Any]:
        response = await self._request(
            "GET",
            "/open-apis/authen/v1/user_info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return response.get("data", response)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        client = self._client or httpx.AsyncClient(
            base_url=self._settings.FEISHU_BASE_URL,
            timeout=10.0,
            trust_env=False,
        )
        owns_client = self._client is None
        try:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Feishu OAuth request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        if payload.get("code", 0) != 0:
            message = payload.get("msg") or payload.get("message") or "Feishu OAuth request failed"
            raise HTTPException(status_code=502, detail=message)
        return payload
