from __future__ import annotations

from typing import Any

from app.services.llm_client import LlmClient


class DummyResponse:
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
