from __future__ import annotations

from app.config import Settings
from app.services.llm_client import LlmClient


def test_llm_client_uses_agent_provider_when_present(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "app.services.llm_client.get_settings",
        lambda: Settings(
            AGENT_API_KEY="agent-key",
            AGENT_API_BASE="https://agent.example.com",
            AGENT_MODEL="agent-model",
            VOLCENGINE_API_KEY="volc-key",
            VOLCENGINE_ENDPOINT="https://volc.example.com",
            VOLCENGINE_MODEL="volc-model",
        ),
    )

    client = LlmClient()

    provider = client._resolve_provider()  # type: ignore[attr-defined]

    assert provider is not None
    assert provider["name"] == "agent"
    assert provider["base"] == "https://agent.example.com"
    assert provider["model"] == "agent-model"


def test_llm_client_falls_back_to_volcengine(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "app.services.llm_client.get_settings",
        lambda: Settings(
            AGENT_API_KEY="",
            AGENT_API_BASE="https://api.deepseek.com",
            VOLCENGINE_API_KEY="volc-key",
            VOLCENGINE_ENDPOINT="https://ark.example.com/api/v3",
            VOLCENGINE_MODEL="volc-model",
        ),
    )

    client = LlmClient()

    provider = client._resolve_provider()  # type: ignore[attr-defined]

    assert provider is not None
    assert provider["name"] == "volcengine"
    assert provider["base"] == "https://ark.example.com/api/v3"
    assert provider["model"] == "volc-model"
