from __future__ import annotations

import asyncio
from typing import Any

from app.config import Settings
from app.core.llm_client import LLMClient
from app.services.llm_client import LlmClient


class DummyResponse:
    is_error = False

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": "ok",
                    }
                }
            ]
        }


def test_llm_client_complete_accepts_custom_timeout(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(*args, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return DummyResponse()

    monkeypatch.setattr("app.services.llm_client.httpx.post", fake_post)

    client = LlmClient()
    monkeypatch.setattr(
        client,
        "_resolve_provider",
        lambda: {
            "base": "https://example.com",
            "key": "secret",
            "model": "demo-model",
        },
    )

    result = client.complete(
        system_prompt="sys",
        user_prompt="user",
        timeout=123,
    )

    assert result == "ok"
    assert captured["timeout"] == 123


def test_llm_client_complete_accepts_custom_max_tokens(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(*args, **kwargs):
        captured["max_tokens"] = kwargs["json"]["max_tokens"]
        return DummyResponse()

    monkeypatch.setattr("app.services.llm_client.httpx.post", fake_post)

    client = LlmClient()
    monkeypatch.setattr(
        client,
        "_resolve_provider",
        lambda: {
            "base": "https://example.com",
            "key": "secret",
            "model": "demo-model",
        },
    )

    result = client.complete(
        system_prompt="sys",
        user_prompt="user",
        max_tokens=9999,
    )

    assert result == "ok"
    assert captured["max_tokens"] == 9999


def test_document_llm_client_appends_chat_completions_for_base_endpoint() -> None:
    client = LLMClient(
        settings_override=Settings(
            VOLCENGINE_ENDPOINT="https://ark.cn-beijing.volces.com/api/v3",
        )
    )

    assert client._endpoint == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


def test_document_llm_client_keeps_explicit_chat_completions_endpoint() -> None:
    client = LLMClient(
        settings_override=Settings(
            VOLCENGINE_ENDPOINT="https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        )
    )

    assert client._endpoint == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


def test_document_llm_client_disables_env_proxy_lookup(monkeypatch) -> None:
    captured: list[dict[str, Any]] = []

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            captured.append(kwargs)

        async def __aenter__(self) -> "DummyAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, *args, **kwargs) -> DummyResponse:
            return DummyResponse()

    monkeypatch.setattr("app.core.llm_client.httpx.AsyncClient", DummyAsyncClient)

    client = LLMClient(
        settings_override=Settings(
            VOLCENGINE_ENDPOINT="https://ark.cn-beijing.volces.com/api/v3",
        )
    )

    asyncio.run(client.generate("sys", "user"))

    assert captured
    assert captured[0]["trust_env"] is False
