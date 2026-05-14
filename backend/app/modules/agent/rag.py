from __future__ import annotations

import logging

from app.config import settings
from app.modules.agent.schemas import AgentChatArtifact, AgentChatRequest, AgentRetrievedContext
from app.modules.bitable.schemas import BitableQueryRequest
from app.modules.bitable.service import BitableService
from app.modules.rag.service import RagService

logger = logging.getLogger(__name__)


class AgentRAGRetriever:
    """Retriever boundary used by the LangGraph retrieval node."""

    def __init__(
        self,
        rag_service: RagService | None = None,
        *,
        bitable_service: BitableService | None = None,
        vector_limit: int = 4,
        bitable_limit: int = 4,
    ) -> None:
        self._rag_service = rag_service
        self._bitable_service = bitable_service
        self._vector_limit = vector_limit
        self._bitable_limit = bitable_limit

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

        if self._bitable_service is not None:
            try:
                workspace_id = self._workspace_id(request)
                response = await self._bitable_service.query_records(
                    BitableQueryRequest(
                        workspace_id=workspace_id,
                        query=request.message,
                        limit=self._bitable_limit,
                    ),
                    created_by=self._created_by_from_request(request),
                )
                for record in response.records:
                    chunks.append(
                        AgentRetrievedContext(
                            source_id=record.record_id,
                            source_type="bitable",
                            title=record.title,
                            content=record.content,
                            score=record.score,
                            metadata={
                                "source_id": record.source_id,
                                "source_name": record.source_name,
                                "table_id": record.table_id,
                                "table_name": record.table_name,
                                "record_url": record.record_url,
                                "fields": record.fields,
                            },
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Agent Bitable retrieval failed session=%s: %s", request.session_id, exc)

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

    def _workspace_id(self, request: AgentChatRequest) -> str:
        if request.sender and isinstance(request.sender.get("workspace_id"), str):
            return str(request.sender["workspace_id"])
        return settings.BITABLE_DEFAULT_WORKSPACE_ID

    def _created_by_from_request(self, request: AgentChatRequest) -> str | None:
        if not request.sender:
            return None
        raw = (
            request.sender.get("platform_user_id")
            or request.sender.get("sender_open_id")
            or request.sender.get("sender_union_id")
        )
        return str(raw) if raw else None
