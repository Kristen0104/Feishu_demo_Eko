from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings


class LlmClient:
    def __init__(self) -> None:
        self._settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self._resolve_provider())

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        provider = self._resolve_provider()
        if provider is None:
            raise RuntimeError("LLM client is not configured")

        response = httpx.post(
            f"{str(provider['base']).rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider['key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            },
            timeout=60,
            trust_env=False,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"].strip()

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        content = self.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        return json.loads(content)

    def _resolve_provider(self) -> dict[str, Any] | None:
        if self._settings.AGENT_API_KEY and self._settings.AGENT_API_BASE:
            return {
                "name": "agent",
                "base": self._settings.AGENT_API_BASE,
                "key": self._settings.AGENT_API_KEY,
                "model": self._settings.AGENT_MODEL,
            }
        if self._settings.VOLCENGINE_API_KEY and self._settings.VOLCENGINE_ENDPOINT:
            return {
                "name": "volcengine",
                "base": self._settings.VOLCENGINE_ENDPOINT,
                "key": self._settings.VOLCENGINE_API_KEY,
                "model": self._settings.VOLCENGINE_MODEL,
            }
        return None
