from __future__ import annotations

import asyncio

import httpx

from app.config import Settings
from app.modules.rag.embeddings import DeterministicEmbeddingClient
from app.modules.rag.embeddings import OpenAICompatibleEmbeddingClient
from app.modules.rag.embeddings import build_embedding_client


def test_openai_compatible_embedding_client_sends_gitee_failover_header_and_dimensions(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeAsyncClient:
        def __init__(self, *, timeout: float, trust_env: bool) -> None:
            calls.append({"timeout": timeout, "trust_env": trust_env})

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, headers: dict[str, str], json: dict):
            calls.append({"url": url, "headers": headers, "json": json})
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "object": "list",
                    "model": "Qwen3-Embedding-8B",
                    "data": [
                        {"object": "embedding", "index": 0, "embedding": [0.1, 0.2]},
                    ],
                    "usage": {"prompt_tokens": 1, "total_tokens": 1},
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    client = OpenAICompatibleEmbeddingClient(
        api_base="https://ai.gitee.com/v1",
        api_key="gitee-token",
        model="Qwen3-Embedding-8B",
        dimensions=2,
        failover_enabled=True,
    )

    embeddings = asyncio.run(client.embed(["Today is sunny."]))

    assert embeddings == [[0.1, 0.2]]
    request = calls[1]
    assert request["url"] == "https://ai.gitee.com/v1/embeddings"
    assert request["headers"]["Authorization"] == "Bearer gitee-token"
    assert request["headers"]["X-Failover-Enabled"] == "true"
    assert request["json"] == {
        "model": "Qwen3-Embedding-8B",
        "input": ["Today is sunny."],
        "dimensions": 2,
    }


def test_build_embedding_client_does_not_reuse_chat_key_for_explicit_embedding_base() -> None:
    client = build_embedding_client(
        Settings(
            AGENT_API_BASE="https://api.deepseek.com",
            AGENT_API_KEY="deepseek-chat-key",
            AGENT_EMBEDDING_API_BASE="https://ai.gitee.com/v1",
            AGENT_EMBEDDING_API_KEY="",
            RAG_EMBEDDING_DIMENSIONS=1024,
        )
    )

    assert isinstance(client, DeterministicEmbeddingClient)
