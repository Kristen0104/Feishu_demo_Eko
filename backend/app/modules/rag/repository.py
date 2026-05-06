from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.models import RagChunk, RagFile


class RagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_file(self, *, filename: str, source: str, content_hash: str, metadata: dict[str, Any]) -> RagFile:
        existing = await self._session.scalar(
            select(RagFile).where(RagFile.source == source, RagFile.content_hash == content_hash)
        )
        if existing is not None:
            existing.filename = filename
            existing.file_metadata = metadata
            await self._session.flush()
            return existing

        file = RagFile(
            filename=filename,
            file_path=source[:512],
            file_type="text",
            status="indexed",
            source=source,
            content_hash=content_hash,
            file_metadata=metadata,
        )
        self._session.add(file)
        await self._session.flush()
        return file

    async def replace_chunks(self, file_id: str, chunks: list[dict[str, Any]]) -> None:
        await self._session.execute(delete(RagChunk).where(RagChunk.file_id == file_id))
        self._session.add_all(
            [
                RagChunk(
                    file_id=file_id,
                    chunk_index=chunk["chunk_index"],
                    title=chunk["title"],
                    content=chunk["content"],
                    token_count=chunk["token_count"],
                    embedding=chunk["embedding"],
                    chunk_metadata=chunk["metadata"],
                )
                for chunk in chunks
            ]
        )
        await self._session.commit()

    async def list_files(self) -> list[tuple[RagFile, int]]:
        chunk_count = func.count(RagChunk.id).label("chunk_count")
        result = await self._session.execute(
            select(RagFile, chunk_count)
            .outerjoin(RagChunk, RagChunk.file_id == RagFile.id)
            .group_by(RagFile.id)
            .order_by(RagFile.created_at.desc())
        )
        return [(file, count) for file, count in result.all()]

    async def delete_file(self, file_id: str) -> bool:
        result = await self._session.execute(delete(RagFile).where(RagFile.id == file_id))
        await self._session.commit()
        return bool(result.rowcount)

    async def search_chunks(self, *, query_embedding: list[float], query: str, limit: int) -> list[dict[str, Any]]:
        _ = query
        distance = RagChunk.embedding.cosine_distance(query_embedding).label("distance")
        result = await self._session.execute(
            select(RagChunk, RagFile, distance)
            .join(RagFile, RagFile.id == RagChunk.file_id)
            .order_by(distance)
            .limit(limit)
        )
        hits: list[dict[str, Any]] = []
        for chunk, file, raw_distance in result.all():
            distance_value = float(raw_distance or 0.0)
            hits.append(
                {
                    "chunk_id": chunk.id,
                    "file_id": file.id,
                    "filename": file.filename,
                    "source": file.source,
                    "content": chunk.content,
                    "score": max(0.0, min(1.0, 1.0 - distance_value)),
                    "metadata": {**(file.file_metadata or {}), **(chunk.chunk_metadata or {})},
                }
            )
        return hits
