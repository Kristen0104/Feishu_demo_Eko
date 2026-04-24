"""
飞书 API 服务模块
提供 tenant_access_token 管理、群消息获取、消息内容解析等功能
"""
import httpx
import time
import asyncio
from functools import lru_cache

from app.config import settings


class FeishuTokenCache:
    """tenant_access_token 缓存，自动续期"""

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
            raise Exception(f"Failed to get token: {data}")

        self._token = data["tenant_access_token"]
        self._expire_at = time.time() + data.get("expire", 7200)
        return self._token


feishu_token_cache = FeishuTokenCache()


async def get_tenant_token() -> str:
    """获取 tenant_access_token"""
    return await feishu_token_cache.get_token()


async def fetch_group_messages(
    chat_id: str,
    page_size: int = 100,
    start_time: int | None = None,
    end_time: int | None = None,
) -> dict:
    """
    获取群聊天记录

    Args:
        chat_id: 群 ID
        page_size: 每页数量
        start_time: 开始时间戳(秒)
        end_time: 结束时间戳(秒)

    Returns:
        {
            "items": [...],
            "has_more": bool,
            "page_token": str
        }
    """
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
        raise Exception(f"Failed to fetch messages: {data}")

    return {
        "items": data.get("data", {}).get("items", []),
        "has_more": data.get("data", {}).get("has_more", False),
        "page_token": data.get("data", {}).get("page_token", ""),
    }


def parse_message_content(message: dict) -> str:
    """
    解析消息内容
    飞书推送事件: {"content": "{\"text\":\"xxx\"}"}
    消息列表: {"body": {"content": "{\"text\":\"xxx\"}"}}
    """
    import json
    content = ""

    # 优先从 body.content 取 (消息列表结构)
    if isinstance(message, dict):
        body = message.get("body", {})
        if isinstance(body, dict):
            content = body.get("content", "")

        # 如果没有 body.content，尝试直接取 content (推送事件结构)
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
