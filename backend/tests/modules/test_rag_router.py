from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.rag.dependencies import get_rag_service
from app.modules.rag.router import router
from app.modules.rag.schemas import RagFileCreateRequest, RagFileSchema, RagSearchResultSchema


class OverrideRagService:
    deleted_file_id: str | None = None

    async def list_files(self) -> list[RagFileSchema]:
        return [
            RagFileSchema(
                file_id="rag_file_1",
                filename="knowledge.md",
                source="feishu://doc/knowledge",
                chunk_count=2,
            )
        ]

    async def ingest_file(self, payload: RagFileCreateRequest) -> RagFileSchema:
        return RagFileSchema(
            file_id="rag_file_2",
            filename=payload.filename,
            source=payload.source,
            chunk_count=3,
            metadata=payload.metadata,
        )

    async def search(self, query: str, limit: int = 8) -> list[RagSearchResultSchema]:
        _ = limit
        return [
            RagSearchResultSchema(
                chunk_id="rag_chunk_1",
                source_id="rag_file_1",
                source_type="knowledge_doc",
                title="knowledge.md",
                content=f"命中：{query}",
                score=0.88,
                metadata={"source": "feishu://doc/knowledge"},
            )
        ]

    async def delete_file(self, file_id: str) -> bool:
        self.deleted_file_id = file_id
        return file_id == "rag_file_1"


def _build_client() -> TestClient:
    app = FastAPI()
    service = OverrideRagService()
    app.include_router(router, prefix="/api/v1/rag")
    app.dependency_overrides[get_rag_service] = lambda: service
    client = TestClient(app)
    client.app.state.override_rag_service = service
    return client


def test_rag_file_ingest_contract_returns_indexed_file() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/rag/files",
        json={
            "filename": "anime.md",
            "source": "feishu://doc/anime",
            "content": "动漫行业资料",
            "metadata": {"workspace_id": "demo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["file_id"] == "rag_file_2"
    assert payload["data"]["chunk_count"] == 3
    assert payload["data"]["metadata"]["workspace_id"] == "demo"


def test_rag_file_upload_contract_parses_and_indexes_file() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/rag/files/upload",
        files={"file": ("knowledge.md", b"# Knowledge\n\nRAG upload text", "text/markdown")},
        data={"metadata": '{"workspace_id":"demo"}'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["filename"] == "knowledge.md"
    assert payload["data"]["source"] == "browser-upload://knowledge.md"
    assert payload["data"]["metadata"]["workspace_id"] == "demo"
    assert payload["data"]["metadata"]["file_type"] == "markdown"


def test_rag_search_contract_returns_sources_and_scores() -> None:
    client = _build_client()

    response = client.get("/api/v1/rag/search", params={"query": "动漫 PPT", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["query"] == "动漫 PPT"
    assert payload["data"]["results"][0]["source_id"] == "rag_file_1"
    assert payload["data"]["results"][0]["score"] == 0.88


def test_rag_file_delete_contract_removes_indexed_file() -> None:
    client = _build_client()

    response = client.delete("/api/v1/rag/files/rag_file_1")

    assert response.status_code == 200
    assert response.json()["data"] is True
    assert client.app.state.override_rag_service.deleted_file_id == "rag_file_1"


def test_rag_file_delete_contract_returns_404_for_missing_file() -> None:
    client = _build_client()

    response = client.delete("/api/v1/rag/files/missing")

    assert response.status_code == 404
