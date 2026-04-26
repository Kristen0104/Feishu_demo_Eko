"""
LLM 大模型服务模块
统一封装 DeepSeek 和 火山引擎(Volcengine) API 调用
支持流式和非流式响应
"""
# TODO(PRD-4.2): route prompt construction through intent/workspace/RAG modules so generation can consume chat context, Bitable data, and knowledge hits.
import asyncio
import json
from typing import AsyncGenerator, Optional
import httpx

from app.config import settings


class LLMService:
    """大模型服务，支持 DeepSeek 和 火山引擎(Volcengine)"""

    @property
    def provider(self) -> str:
        return "volcengine" if settings.VOLCENGINE_API_KEY else "deepseek"

    @property
    def api_url(self) -> str:
        if self.provider == "volcengine":
            return f"{settings.VOLCENGINE_ENDPOINT}/chat/completions"
        return f"{settings.AGENT_API_BASE}/chat/completions"

    @property
    def api_key(self) -> str:
        if self.provider == "volcengine":
            return settings.VOLCENGINE_API_KEY
        return settings.AGENT_API_KEY

    @property
    def model(self) -> str:
        if self.provider == "volcengine":
            return settings.VOLCENGINE_MODEL
        return settings.AGENT_MODEL

    async def chat(
        self,
        messages: list[dict],
        stream: bool = False,
        system_prompt: Optional[str] = None,
    ) -> dict | AsyncGenerator:
        """
        通用对话接口

        Args:
            messages: [{"role": "user/assistant", "content": "..."}]
            stream: 是否流式返回
            system_prompt: 系统提示词

        Returns:
            非流式: {"content": "...", "usage": {...}}
            流式: AsyncGenerator yield {"chunk": "...", "done": bool}
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": all_messages,
            "stream": stream,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            if stream:
                return self._stream_response(client, self.api_url, headers, payload)
            else:
                response = await self._post_with_retry(client, headers, payload)
                data = response.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                }

    async def _post_with_retry(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        payload: dict,
    ) -> httpx.Response:
        """对非流式 LLM 调用做轻量退避，避免临时限流直接让任务失败。"""
        retry_statuses = {429, 500, 502, 503, 504}
        for attempt in range(3):
            try:
                response = await client.post(self.api_url, headers=headers, json=payload)
                if response.status_code not in retry_statuses or attempt == 2:
                    response.raise_for_status()
                    return response

                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = min(float(retry_after), 8.0)
                else:
                    delay = 1.5 * (2 ** attempt)
            except httpx.TransportError:
                if attempt == 2:
                    raise
                delay = 1.5 * (2 ** attempt)
            await asyncio.sleep(delay)

        raise RuntimeError("LLM request retry loop exited unexpectedly")

    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict,
        payload: dict,
    ) -> AsyncGenerator:
        """通用的流式响应处理"""
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield {"chunk": "", "done": True}
                        break
                    try:
                        parsed = json.loads(data)
                        chunk = parsed["choices"][0]["delta"].get("content", "")
                        if chunk:
                            yield {"chunk": chunk, "done": False}
                    except json.JSONDecodeError:
                        continue


llm_service = LLMService()
