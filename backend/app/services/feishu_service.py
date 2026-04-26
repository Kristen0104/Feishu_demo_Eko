"""Compatibility wrapper for the Feishu module."""

from __future__ import annotations

from ..modules.feishu import FeishuTokenCache, fetch_group_messages, get_tenant_token, parse_message_content

__all__ = [
    "FeishuTokenCache",
    "fetch_group_messages",
    "get_tenant_token",
    "parse_message_content",
]

