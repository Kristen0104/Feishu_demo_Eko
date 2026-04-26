"""Async provider adapter for AI-generated SVG pages."""

from __future__ import annotations

import asyncio
import os
import re
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass
from typing import Any

try:
    from app.config import settings
except ModuleNotFoundError:  # pragma: no cover - direct test import fallback
    from backend.app.config import settings

from .templates import validate_svg


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key_env: str
    base_url_env: str
    model_env: str
    default_base_url: str
    default_model: str


PROVIDERS: dict[str, ProviderConfig] = {
    "openai": ProviderConfig("openai", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "https://api.openai.com/v1", "gpt-4.1-mini"),
    "gemini": ProviderConfig("gemini", "GEMINI_API_KEY", "GEMINI_BASE_URL", "GEMINI_MODEL", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
    "qwen": ProviderConfig("qwen", "QWEN_API_KEY", "QWEN_BASE_URL", "QWEN_MODEL", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    "zhipu": ProviderConfig("zhipu", "ZHIPU_API_KEY", "ZHIPU_BASE_URL", "ZHIPU_MODEL", "https://open.bigmodel.cn/api/paas/v4", "glm-4-flash"),
    "volcengine": ProviderConfig("volcengine", "VOLCENGINE_API_KEY", "VOLCENGINE_ENDPOINT", "VOLCENGINE_MODEL", "https://ark.cn-beijing.volces.com/api/v3", "ep-20260423222610-xbx2l"),
}


class ApiClient:
    """OpenAI-compatible chat-completions adapter with retry and timeout."""

    def __init__(
        self,
        backend: str | None = None,
        timeout: float = 60.0,
        retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.backend = (backend or _resolve_backend()).lower()
        if self.backend not in PROVIDERS:
            raise ValueError(f"Unsupported IMAGE_BACKEND: {self.backend}")
        self.provider = PROVIDERS[self.backend]
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay

    @property
    def api_key(self) -> str:
        return _read_config(self.provider.api_key_env, "")

    @property
    def base_url(self) -> str:
        return _read_config(self.provider.base_url_env, self.provider.default_base_url).rstrip("/")

    @property
    def model(self) -> str:
        return _read_config(self.provider.model_env, self.provider.default_model)

    async def generate_svg(self, page: dict[str, Any], design_context: dict[str, Any] | None = None) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.provider.api_key_env} is required for AI SVG generation")

        prompt = _build_prompt(page, design_context or {})
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Generate one PPT-compatible SVG. Return only the SVG markup."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                svg = await self._post_chat(payload)
                validate_svg(svg)
                return svg
            except Exception as exc:
                last_error = exc
                if attempt < self.retries - 1:
                    await asyncio.sleep(self.retry_delay)

        raise RuntimeError(f"AI SVG generation failed after {self.retries} attempts: {last_error}") from last_error

    async def _post_chat(self, payload: dict[str, Any]) -> str:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return _extract_svg(data["choices"][0]["message"]["content"])


def _build_prompt(page: dict[str, Any], design_context: dict[str, Any]) -> str:
    return (
        "Use viewBox=\"0 0 1280 720\". Avoid mask, style, class, foreignObject, textPath, "
        "rgba(), group opacity, symbol/use, scripts, and animations. "
        f"Design context: {design_context}. Page data: {page}."
    )


def _resolve_backend() -> str:
    explicit_backend = _read_config("IMAGE_BACKEND", "")
    if explicit_backend:
        return explicit_backend

    for backend_name, provider in PROVIDERS.items():
        if _read_config(provider.api_key_env, ""):
            return backend_name
    return "openai"


def _read_config(name: str, default: str) -> str:
    env_value = os.getenv(name)
    if env_value:
        return env_value

    settings_value = getattr(settings, name, "")
    if settings_value:
        return str(settings_value)
    dotenv_value = _dotenv_values().get(name, "")
    if dotenv_value:
        return dotenv_value
    return default


@lru_cache(maxsize=1)
def _dotenv_values() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _extract_svg(content: str) -> str:
    match = re.search(r"<svg\b.*?</svg>", content, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("AI response did not contain an SVG document")
    return match.group(0)
