from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RagFile(Base):
    __tablename__ = "rag_files"
    __table_args__ = (UniqueConstraint("source", "content_hash", name="uq_rag_files_source_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: uuid4().hex)
    user_id: Mapped[str] = mapped_column(String(36), default="system", nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), default="text", nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), default="indexed", nullable=True)
    source: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    chunks: Mapped[list["RagChunk"]] = relationship(back_populates="file", cascade="all, delete-orphan")


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (UniqueConstraint("file_id", "chunk_index", name="uq_rag_chunks_file_index"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    file_id: Mapped[str] = mapped_column(ForeignKey("rag_files.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.RAG_EMBEDDING_DIMENSIONS), nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    file: Mapped[RagFile] = relationship(back_populates="chunks")
