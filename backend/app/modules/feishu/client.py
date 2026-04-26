"""Feishu API helpers."""

from __future__ import annotations

import asyncio
import json
import time

import httpx

from app.config import settings


# TODO(PRD-2.2): split token management, chat history retrieval, card updates, and Bitable operations into separate files.
class FeishuTokenCache:
    """tenant_access_token cache with automatic renewal."""

    def __init__(self):
        self._token: str | None = None
        self._expire_at: float = 0

    async def get_token(self) -> str:
        if self._token and time.time() < self._expire_at - 60:
            return self._token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": settings.FEISHU_APP_ID,
            "app_secret": settings.FEISHU_APP_SECRET,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get token: {data}")

        self._token = data["tenant_access_token"]
        self._expire_at = time.time() + data.get("expire", 7200)
        return self._token


feishu_token_cache = FeishuTokenCache()


async def get_tenant_token() -> str:
    """Get tenant access token."""
    return await feishu_token_cache.get_token()


async def fetch_group_messages(
    chat_id: str,
    page_size: int = 100,
    start_time: int | None = None,
    end_time: int | None = None,
) -> dict:
    """Fetch group chat messages."""
    token = await get_tenant_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id_type": "chat",
        "container_id": chat_id,
        "page_size": page_size,
    }
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("code") != 0:
        raise RuntimeError(f"Failed to fetch messages: {data}")

    return {
        "items": data.get("data", {}).get("items", []),
        "has_more": data.get("data", {}).get("has_more", False),
        "page_token": data.get("data", {}).get("page_token", ""),
    }


def parse_message_content(message: dict) -> str:
    """Parse a Feishu message payload into plain text."""
    content = ""

    if isinstance(message, dict):
        body = message.get("body", {})
        if isinstance(body, dict):
            content = body.get("content", "")
        if not content:
            content = message.get("content", "")

    if not content:
        return ""

    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            text = obj.get("text", "")
            if text:
                return text
            return str(obj)
        return str(obj)
    except json.JSONDecodeError:
        return content

