from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BitableSource(Base):
    __tablename__ = "bitable_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"bs_{uuid4().hex}")
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    app_token: Mapped[str] = mapped_column(String(255), nullable=False)
    table_id: Mapped[str] = mapped_column(String(255), nullable=False)
    view_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), default="both", nullable=False)
    title_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_mapping: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_schema_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_check_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_check_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class BitableArchiveLink(Base):
    __tablename__ = "bitable_archive_links"
    __table_args__ = (
        UniqueConstraint("session_id", "artifact_kind", "source_id", name="uq_bitable_archive_session_kind_source"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"bal_{uuid4().hex}")
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artifact_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    record_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    archive_status: Mapped[str] = mapped_column(String(32), nullable=False)
    archive_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
