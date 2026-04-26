"""RAG storage and retrieval placeholders."""

from __future__ import annotations

# TODO(PRD-2.2): implement document ingest, vector indexing, semantic search, and 回流 into the knowledge base.


async def ingest_document(*args, **kwargs):
    raise NotImplementedError("RAG ingest is not implemented yet")


async def search_documents(*args, **kwargs):
    raise NotImplementedError("RAG search is not implemented yet")

