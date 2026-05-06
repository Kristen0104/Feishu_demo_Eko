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

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 60,
        max_tokens: int | None = None,
    ) -> str:
        provider = self._resolve_provider()
        if provider is None:
            raise RuntimeError("LLM client is not configured")

        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = httpx.post(
            f"{str(provider['base']).rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider['key']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
            trust_env=False,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"].strip()

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 60,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        content = self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout=timeout,
            max_tokens=max_tokens,
        )
        stripped = content.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                stripped = "\n".join(lines[1:-1]).strip()
        return json.loads(stripped)

    def complete_json_with_options(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 60,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        return self.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout=timeout,
            max_tokens=max_tokens,
        )

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
