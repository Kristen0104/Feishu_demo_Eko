from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.modules.rag.embeddings import DeterministicEmbeddingClient
from app.modules.rag.schemas import RagFileCreateRequest
from app.modules.rag.service import RagService


@dataclass
class StoredFile:
    id: str
    filename: str
    source: str
    content_hash: str
    metadata: dict[str, str]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InMemoryRagRepository:
    def __init__(self) -> None:
        self.files: list[StoredFile] = []
        self.chunks: list[dict] = []

    async def create_file(self, *, filename: str, source: str, content_hash: str, metadata: dict) -> StoredFile:
        file = StoredFile(
            id=f"rag_file_{len(self.files) + 1}",
            filename=filename,
            source=source,
            content_hash=content_hash,
            metadata=metadata,
        )
        self.files.append(file)
        return file

    async def replace_chunks(self, file_id: str, chunks: list[dict]) -> None:
        self.chunks = [chunk for chunk in self.chunks if chunk["file_id"] != file_id]
        self.chunks.extend(chunks)

    async def list_files(self) -> list[tuple[StoredFile, int]]:
        return [(file, sum(1 for chunk in self.chunks if chunk["file_id"] == file.id)) for file in self.files]

    async def search_chunks(self, *, query_embedding: list[float], query: str, limit: int) -> list[dict]:
        _ = query_embedding
        terms = [token for token in query.lower().split() if token]
        scored: list[dict] = []
        for chunk in self.chunks:
            content = chunk["content"].lower()
            lexical_hits = sum(1 for term in terms if term in content)
            if lexical_hits <= 0:
                continue
            scored.append(
                {
                    **chunk,
                    "chunk_id": f"chunk_{chunk['chunk_index'] + 1}",
                    "filename": self.files[0].filename,
                    "source": self.files[0].source,
                    "score": min(1.0, lexical_hits / max(len(terms), 1)),
                }
            )
        return scored[:limit]


def test_rag_service_ingests_splits_and_searches_chunks() -> None:
    repository = InMemoryRagRepository()
    service = RagService(
        repository=repository,  # type: ignore[arg-type]
        embedding_client=DeterministicEmbeddingClient(dimensions=8),
        chunk_size=36,
        chunk_overlap=8,
    )

    file = asyncio.run(
        service.ingest_file(
            RagFileCreateRequest(
                filename="anime-market.md",
                source="feishu://doc/anime",
                content=(
                    "动漫行业正在向 IP 化、全球发行和衍生品联动发展。"
                    "这个资料用于 PPT 生成。"
                    "平台方正在加强海外渠道、内容授权和线下商业化协同。"
                    "制作公司也在关注模型工具对分镜、宣发和粉丝运营的提效。"
                ),
                metadata={"workspace_id": "demo"},
            )
        )
    )
    results = asyncio.run(service.search("全球发行 PPT", limit=3))

    assert file.file_id == "rag_file_1"
    assert file.chunk_count >= 2
    assert results
    assert results[0].source_id == "rag_file_1"
    assert results[0].source_type == "knowledge_doc"
    assert results[0].title == "anime-market.md"
    assert "全球发行" in results[0].content
    assert results[0].metadata["workspace_id"] == "demo"
