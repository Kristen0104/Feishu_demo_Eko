from __future__ import annotations

import logging

from app.modules.agent.schemas import AgentChatArtifact, AgentChatRequest, AgentRetrievedContext
from app.modules.rag.service import RagService

logger = logging.getLogger(__name__)


class AgentRAGRetriever:
    """Retriever boundary used by the LangGraph retrieval node."""

    def __init__(self, rag_service: RagService | None = None, *, vector_limit: int = 4) -> None:
        self._rag_service = rag_service
        self._vector_limit = vector_limit

    async def retrieve(
        self,
        request: AgentChatRequest,
        *,
        current_artifact: AgentChatArtifact | None = None,
    ) -> list[AgentRetrievedContext]:
        chunks: list[AgentRetrievedContext] = []

        if self._rag_service is not None:
            try:
                for result in await self._rag_service.search(request.message, limit=self._vector_limit):
                    chunks.append(
                        AgentRetrievedContext(
                            source_id=result.source_id,
                            source_type=result.source_type,
                            title=result.title,
                            content=result.content,
                            score=result.score,
                            metadata=result.metadata,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Agent RAG vector search failed session=%s: %s", request.session_id, exc)

        chunks.extend(self._request_context_chunks(request, current_artifact=current_artifact))
        return chunks[:8]

    def _request_context_chunks(
        self,
        request: AgentChatRequest,
        *,
        current_artifact: AgentChatArtifact | None,
    ) -> list[AgentRetrievedContext]:
        chunks: list[AgentRetrievedContext] = []
        query = request.message.lower()

        if request.context is not None:
            for index, doc in enumerate(request.context.knowledge_docs):
                score = self._score(query, f"{doc.title}\n{doc.content}")
                if score <= 0 and chunks:
                    continue
                chunks.append(
                    AgentRetrievedContext(
                        source_id=doc.source or f"knowledge_doc_{index + 1}",
                        source_type="knowledge_doc",
                        title=doc.title,
                        content=doc.content,
                        score=score or 0.5,
                        metadata={"source": doc.source} if doc.source else {},
                    )
                )

            for index, message in enumerate(request.context.chat_history[-6:]):
                content = message.content.strip()
                if not content:
                    continue
                score = self._score(query, content)
                chunks.append(
                    AgentRetrievedContext(
                        source_id=f"chat_history_{index + 1}",
                        source_type="chat_history",
                        title=f"{message.role} 上下文",
                        content=content,
                        score=score or 0.35,
                        metadata={"role": message.role},
                    )
                )

        if current_artifact is not None:
            summary_parts = [
                f"类型：{current_artifact.kind}",
                current_artifact.result_summary or "",
                current_artifact.content or "",
                current_artifact.sharing_url or "",
            ]
            content = "\n".join(part for part in summary_parts if part).strip()
            if content:
                chunks.append(
                    AgentRetrievedContext(
                        source_id="current_artifact",
                        source_type="artifact",
                        title="当前产物",
                        content=content[:1600],
                        score=0.8,
                        metadata={"kind": current_artifact.kind},
                    )
                )

        return chunks

    def _score(self, query: str, content: str) -> float:
        normalized = content.lower()
        tokens = [token for token in query.replace("，", " ").replace("。", " ").split() if token]
        if not tokens:
            return 0.5
        hits = sum(1 for token in tokens if token in normalized)
        return min(1.0, hits / max(len(tokens), 1))
