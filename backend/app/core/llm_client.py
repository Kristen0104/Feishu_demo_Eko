"""
LLM 客户端封装
支持火山引擎Doubao模型调用，用于文档生成
"""
from __future__ import annotations

import json
from typing import AsyncIterator
import httpx

from app.config import Settings, settings


class LLMRequestError(RuntimeError):
    """Raised when the upstream LLM API rejects a request."""

    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message

    @classmethod
    def from_response(cls, response: httpx.Response) -> "LLMRequestError":
        message = f"LLM request failed with HTTP {response.status_code}"
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                error_code = error.get("code")
                error_message = error.get("message")
                if error_code and error_message:
                    message = f"{error_code}: {error_message}"
                elif error_message:
                    message = str(error_message)

        return cls(status_code=response.status_code, message=message)


class LLMClient:
    """OpenAI-compatible LLM client used by agent/document modules."""

    def __init__(self, settings_override: Settings | None = None) -> None:
        active_settings = settings_override or settings
        if active_settings.AGENT_API_KEY and active_settings.AGENT_API_BASE:
            self._api_key = active_settings.AGENT_API_KEY
            self._endpoint = self._normalize_endpoint(active_settings.AGENT_API_BASE)
            self._model = active_settings.AGENT_MODEL
            self._supports_thinking_option = True
        else:
            self._api_key = active_settings.VOLCENGINE_API_KEY
            self._endpoint = self._normalize_endpoint(active_settings.VOLCENGINE_ENDPOINT)
            self._model = active_settings.VOLCENGINE_MODEL
            self._supports_thinking_option = False
        self._thinking_enabled = active_settings.AGENT_THINKING_ENABLED
        self._timeout = 300  # 长文档生成允许5分钟超时

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        normalized = endpoint.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """非流式生成完整文本"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if self._supports_thinking_option and not self._thinking_enabled:
            payload["thinking"] = {"type": "disabled"}

        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            response = await client.post(
                self._endpoint,
                headers=headers,
                json=payload,
            )
            if response.is_error:
                raise LLMRequestError.from_response(response)
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """流式逐块输出"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if self._supports_thinking_option and not self._thinking_enabled:
            payload["thinking"] = {"type": "disabled"}

        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            async with client.stream(
                "POST",
                self._endpoint,
                headers=headers,
                json=payload,
            ) as response:
                if response.is_error:
                    error_body = await response.aread()
                    error_response = httpx.Response(
                        status_code=response.status_code,
                        headers=response.headers,
                        content=error_body,
                        request=response.request,
                    )
                    raise LLMRequestError.from_response(error_response)
                async for chunk in response.aiter_lines():
                    if not chunk.strip() or chunk == "data: [DONE]":
                        continue
                    if chunk.startswith("data: "):
                        chunk = chunk[6:]
                    try:
                        data = json.loads(chunk)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue


def get_llm_client() -> LLMClient:
    """获取LLM客户端单例"""
    return LLMClient()
