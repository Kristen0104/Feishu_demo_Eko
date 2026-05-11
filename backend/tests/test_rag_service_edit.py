from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.rag.schemas import RagFileCreateRequest, RagFileUpdateRequest
from app.modules.rag.service import RagService


class _File:
    def __init__(self, *, file_id: str, filename: str, source: str, content_hash: str, metadata: dict, raw_content: str) -> None:
        self.id = file_id
        self.filename = filename
        self.source = source
        self.file_path = source
        self.content_hash = content_hash
        self.file_metadata = metadata
        self.raw_content = raw_content
        self.created_at = None


class _Repository:
    def __init__(self) -> None:
        self.file: _File | None = None
        self.chunks: list[dict] = []

    async def create_file(self, *, filename, source, content_hash, metadata, raw_content):  # noqa: ANN001
        self.file = _File(
            file_id="rag_1",
            filename=filename,
            source=source,
            content_hash=content_hash,
            metadata=metadata,
            raw_content=raw_content,
        )
        return self.file

    async def get_file(self, file_id):  # noqa: ANN001
        if self.file and self.file.id == file_id:
            return self.file
        return None

    async def get_content_from_chunks(self, file_id):  # noqa: ANN001
        if not self.chunks:
            return None
        return "\n\n".join(chunk["content"] for chunk in self.chunks)

    async def update_file(self, file_id, *, filename=None, source=None, content_hash=None, raw_content=None, metadata=None):  # noqa: ANN001
        file = await self.get_file(file_id)
        if file is None:
            return None
        if filename is not None:
            file.filename = filename
        if source is not None:
            file.source = source
            file.file_path = source
        if content_hash is not None:
            file.content_hash = content_hash
        if raw_content is not None:
            file.raw_content = raw_content
        if metadata is not None:
            file.file_metadata = metadata
        if source is not None or metadata is not None:
            next_metadata = metadata if metadata is not None else file.file_metadata
            next_source = source if source is not None else file.source
            self.chunks = [
                {**chunk, "metadata": {"source": next_source, **next_metadata}}
                for chunk in self.chunks
            ]
        return file

    async def replace_chunks(self, file_id, chunks):  # noqa: ANN001
        self.chunks = chunks

    async def count_chunks(self, file_id):  # noqa: ANN001
        return len(self.chunks)


class _EmbeddingClient:
    async def embed(self, texts):  # noqa: ANN001
        return [[float(index), 0.0, 0.0] for index, _ in enumerate(texts)]


class RagServiceEditTest(IsolatedAsyncioTestCase):
    async def test_update_file_metadata_without_reindexing(self) -> None:
        repository = _Repository()
        service = RagService(repository, embedding_client=_EmbeddingClient(), chunk_size=20, chunk_overlap=0)
        created = await service.ingest_file(
            RagFileCreateRequest(
                filename="old.md",
                source="source://old",
                content="alpha beta gamma",
                metadata={"note": "old"},
            )
        )

        updated = await service.update_file(
            created.file_id,
            RagFileUpdateRequest(filename="new.md", source="source://new", metadata={"note": "new"}),
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.filename, "new.md")
        self.assertEqual(updated.source, "source://new")
        self.assertEqual(updated.metadata["note"], "new")
        self.assertEqual(repository.chunks[0]["metadata"]["source"], "source://new")
        self.assertEqual(repository.chunks[0]["metadata"]["note"], "new")

    async def test_get_file_content_returns_raw_content(self) -> None:
        repository = _Repository()
        service = RagService(repository, embedding_client=_EmbeddingClient(), chunk_size=20, chunk_overlap=0)
        created = await service.ingest_file(
            RagFileCreateRequest(
                filename="doc.md",
                source="source://doc",
                content="alpha beta gamma",
                metadata={"note": "preview"},
            )
        )

        content = await service.get_file_content(created.file_id)

        self.assertIsNotNone(content)
        self.assertEqual(content.content, "alpha beta gamma")
        self.assertEqual(content.metadata["note"], "preview")

    async def test_update_file_content_replaces_chunks(self) -> None:
        repository = _Repository()
        service = RagService(repository, embedding_client=_EmbeddingClient(), chunk_size=10, chunk_overlap=0)
        created = await service.ingest_file(
            RagFileCreateRequest(
                filename="doc.md",
                source="source://doc",
                content="alpha beta gamma",
                metadata={},
            )
        )

        updated = await service.update_file(
            created.file_id,
            RagFileUpdateRequest(content="new content for vectors", metadata={"note": "reindexed"}),
        )

        self.assertIsNotNone(updated)
        self.assertGreaterEqual(updated.chunk_count, 1)
        self.assertEqual(repository.file.raw_content, "new content for vectors")
        self.assertEqual(repository.chunks[0]["metadata"]["note"], "reindexed")
        self.assertIn("new content", repository.chunks[0]["content"])

    async def test_update_missing_file_returns_none(self) -> None:
        service = RagService(_Repository(), embedding_client=_EmbeddingClient(), chunk_size=20, chunk_overlap=0)

        updated = await service.update_file("missing", RagFileUpdateRequest(filename="new.md"))

        self.assertIsNone(updated)
