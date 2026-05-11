from __future__ import annotations

import hashlib
from typing import Any

from app.config import settings
from app.modules.rag.embeddings import EmbeddingClient, build_embedding_client
from app.modules.rag.repository import RagRepository
from app.modules.rag.schemas import (
    RagFileContentSchema,
    RagFileCreateRequest,
    RagFileSchema,
    RagFileUpdateRequest,
    RagSearchResultSchema,
)
from app.modules.rag.splitter import TextSplitter


class RagService:
    def __init__(
        self,
        repository: RagRepository,
        *,
        embedding_client: EmbeddingClient | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self._repository = repository
        self._embedding_client = embedding_client or build_embedding_client()
        self._splitter = TextSplitter(
            chunk_size=chunk_size or settings.RAG_CHUNK_SIZE,
            chunk_overlap=chunk_overlap if chunk_overlap is not None else settings.RAG_CHUNK_OVERLAP,
        )

    async def ingest_file(self, payload: RagFileCreateRequest) -> RagFileSchema:
        chunks = self._splitter.split(payload.content)
        embeddings = await self._embedding_client.embed([chunk.content for chunk in chunks])
        content_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
        file = await self._repository.create_file(
            filename=payload.filename,
            source=payload.source,
            content_hash=content_hash,
            metadata=payload.metadata,
            raw_content=payload.content,
        )
        await self._repository.replace_chunks(
            file.id,
            [
                {
                    "file_id": file.id,
                    "chunk_index": chunk.index,
                    "title": payload.filename,
                    "content": chunk.content,
                    "token_count": len(chunk.content),
                    "embedding": embedding,
                    "metadata": {"source": payload.source, **payload.metadata},
                }
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ],
        )
        return self._file_schema(file, len(chunks))

    async def get_file_content(self, file_id: str) -> RagFileContentSchema | None:
        file = await self._repository.get_file(file_id)
        if file is None:
            return None
        chunk_count = await self._repository.count_chunks(file_id)
        raw_content = getattr(file, "raw_content", None)
        content = raw_content if isinstance(raw_content, str) and raw_content else await self._repository.get_content_from_chunks(file_id)
        return RagFileContentSchema(
            **self._file_schema(file, chunk_count).model_dump(),
            content=content or "",
        )

    async def update_file(self, file_id: str, payload: RagFileUpdateRequest) -> RagFileSchema | None:
        existing = await self._repository.get_file(file_id)
        if existing is None:
            return None

        filename = payload.filename.strip() if isinstance(payload.filename, str) else None
        source = payload.source.strip() if isinstance(payload.source, str) else None
        if filename == "":
            filename = None
        if source == "":
            source = None

        metadata = payload.metadata
        content_hash: str | None = None
        if payload.content is not None:
            content = payload.content
            chunks = self._splitter.split(content)
            embeddings = await self._embedding_client.embed([chunk.content for chunk in chunks])
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            chunk_source = source or existing.source
            chunk_title = filename or existing.filename
            next_metadata = metadata if metadata is not None else existing.file_metadata or {}
            await self._repository.replace_chunks(
                file_id,
                [
                    {
                        "file_id": file_id,
                        "chunk_index": chunk.index,
                        "title": chunk_title,
                        "content": chunk.content,
                        "token_count": len(chunk.content),
                        "embedding": embedding,
                        "metadata": {"source": chunk_source, **next_metadata},
                    }
                    for chunk, embedding in zip(chunks, embeddings, strict=True)
                ],
            )

        updated = await self._repository.update_file(
            file_id,
            filename=filename,
            source=source,
            content_hash=content_hash,
            raw_content=payload.content,
            metadata=metadata,
        )
        if updated is None:
            return None
        return self._file_schema(updated, await self._repository.count_chunks(file_id))

    async def list_files(self) -> list[RagFileSchema]:
        return [self._file_schema(file, chunk_count) for file, chunk_count in await self._repository.list_files()]

    async def delete_file(self, file_id: str) -> bool:
        return await self._repository.delete_file(file_id)

    async def search(self, query: str, limit: int = 8) -> list[RagSearchResultSchema]:
        query_embedding = (await self._embedding_client.embed([query]))[0]
        hits = await self._repository.search_chunks(query_embedding=query_embedding, query=query, limit=limit)
        return [
            RagSearchResultSchema(
                chunk_id=hit["chunk_id"],
                source_id=hit["file_id"],
                source_type="knowledge_doc",
                title=hit["filename"],
                content=hit["content"],
                score=hit["score"],
                metadata={"source": hit["source"], **hit.get("metadata", {})},
            )
            for hit in hits
        ]

    def _file_schema(self, file: Any, chunk_count: int) -> RagFileSchema:
        return RagFileSchema(
            file_id=file.id,
            filename=file.filename,
            source=file.source,
            chunk_count=chunk_count,
            metadata=getattr(file, "file_metadata", getattr(file, "metadata", {})) or {},
            created_at=file.created_at.isoformat() if getattr(file, "created_at", None) else None,
        )
