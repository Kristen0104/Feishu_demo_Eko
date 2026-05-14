from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"user_{uuid4().hex}")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500000), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_ext: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    team: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reports_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    languages: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    feishu_accounts: Mapped[list["FeishuAccount"]] = relationship(back_populates="user")
    oauth_tokens: Mapped[list["FeishuOAuthToken"]] = relationship(back_populates="user")


class FeishuAccount(Base):
    __tablename__ = "feishu_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_feishu_accounts_user_id"),
        UniqueConstraint("open_id", name="uq_feishu_accounts_open_id"),
        UniqueConstraint("union_id", name="uq_feishu_accounts_union_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"fa_{uuid4().hex}")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    open_id: Mapped[str] = mapped_column(String(255), nullable=False)
    union_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenant_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="feishu_accounts")


class FeishuOAuthToken(Base):
    __tablename__ = "feishu_oauth_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"fot_{uuid4().hex}")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    access_token: Mapped[str] = mapped_column(String(4096), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    token_type: Mapped[str] = mapped_column(String(32), default="Bearer", nullable=False)
    scope: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="oauth_tokens")
