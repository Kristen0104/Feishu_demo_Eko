from __future__ import annotations

import hashlib
from typing import Protocol

import httpx

from app.config import Settings, settings


class EmbeddingClient(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class DeterministicEmbeddingClient:
    """Stable local embedding fallback for tests and keyless development."""

    def __init__(self, dimensions: int = 1536) -> None:
        self._dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        tokens = [token for token in text.lower().replace("，", " ").replace("。", " ").split() if token]
        if not tokens:
            tokens = [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            vector[index] += 1.0
        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / norm for value in vector]


class OpenAICompatibleEmbeddingClient:
    def __init__(
        self,
        *,
        api_base: str,
        api_key: str,
        model: str,
        dimensions: int,
        failover_enabled: bool = False,
        timeout: float = 60.0,
    ) -> None:
        self._endpoint = self._normalize_endpoint(api_base)
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._failover_enabled = failover_enabled
        self._timeout = timeout

    @staticmethod
    def _normalize_endpoint(api_base: str) -> str:
        normalized = api_base.rstrip("/")
        if normalized.endswith("/embeddings"):
            return normalized
        if normalized.endswith("/chat/completions"):
            normalized = normalized[: -len("/chat/completions")]
        return f"{normalized}/embeddings"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self._model,
            "input": texts,
            "dimensions": self._dimensions,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._failover_enabled:
            headers["X-Failover-Enabled"] = "true"
        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            response = await client.post(self._endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"])]
        return [self._coerce_dimensions(embedding) for embedding in embeddings]

    def _coerce_dimensions(self, embedding: list[float]) -> list[float]:
        if len(embedding) == self._dimensions:
            return embedding
        if len(embedding) > self._dimensions:
            return embedding[: self._dimensions]
        return [*embedding, *([0.0] * (self._dimensions - len(embedding)))]


def build_embedding_client(settings_override: Settings | None = None) -> EmbeddingClient:
    active_settings = settings_override or settings
    if active_settings.AGENT_EMBEDDING_API_BASE:
        api_base = active_settings.AGENT_EMBEDDING_API_BASE
        api_key = active_settings.AGENT_EMBEDDING_API_KEY
    else:
        api_base = active_settings.AGENT_API_BASE
        api_key = active_settings.AGENT_EMBEDDING_API_KEY or active_settings.AGENT_API_KEY
    if api_key and api_key != "your_agent_api_key" and api_base:
        return OpenAICompatibleEmbeddingClient(
            api_base=api_base,
            api_key=api_key,
            model=active_settings.AGENT_EMBEDDING_MODEL,
            dimensions=active_settings.RAG_EMBEDDING_DIMENSIONS,
            failover_enabled=active_settings.AGENT_EMBEDDING_FAILOVER_ENABLED,
        )
    return DeterministicEmbeddingClient(dimensions=active_settings.RAG_EMBEDDING_DIMENSIONS)
