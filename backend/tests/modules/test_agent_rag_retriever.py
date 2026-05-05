from __future__ import annotations

import asyncio

from app.modules.agent.rag import AgentRAGRetriever
from app.modules.agent.schemas import AgentChatRequest
from app.modules.rag.schemas import RagSearchResultSchema


class FakeRagService:
    async def search(self, query: str, limit: int = 8) -> list[RagSearchResultSchema]:
        assert query == "用知识库生成动漫 PPT"
        assert limit == 4
        return [
            RagSearchResultSchema(
                chunk_id="chunk_1",
                source_id="file_1",
                source_type="knowledge_doc",
                title="动漫行业资料",
                content="动漫行业正在向全球发行和 IP 衍生品发展。",
                score=0.92,
                metadata={"source": "feishu://doc/anime"},
            )
        ]


def test_agent_rag_retriever_merges_pgvector_results_with_request_context() -> None:
    retriever = AgentRAGRetriever(rag_service=FakeRagService(), vector_limit=4)  # type: ignore[arg-type]

    chunks = asyncio.run(retriever.retrieve(AgentChatRequest(session_id="s1", message="用知识库生成动漫 PPT")))

    assert chunks[0].source_id == "file_1"
    assert chunks[0].title == "动漫行业资料"
    assert chunks[0].score == 0.92

