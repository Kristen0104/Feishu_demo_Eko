"""
数据库模型模块
定义所有 SQLAlchemy ORM 模型，对应 PostgreSQL 数据库表结构
"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

from ..core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feishu_open_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(256))
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    last_intent: Mapped[str | None] = mapped_column(String(32), nullable=True)  # CHAT/DOC/PPT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="sessions")
    tasks: Mapped[list["Task"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    canvas_elements: Mapped[list["CanvasElement"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str] = mapped_column(String(32))  # CHAT/DOC/PPT
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/running/completed/failed
    plan_steps: Mapped[list | None] = mapped_column(JSON, nullable=True)  # JSON array of steps
    result_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bitable_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="tasks")
    user: Mapped["User"] = relationship()

    Index("idx_tasks_session_id", "session_id")
    Index("idx_tasks_user_id", "user_id")


class CanvasElement(Base):
    __tablename__ = "canvas_elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"))
    element_type: Mapped[str] = mapped_column(String(64))  # shape/text/arrow/card
    data: Mapped[dict] = mapped_column(JSON)  # Tldraw element JSON
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="canvas_elements")

    Index("idx_canvas_session_id", "session_id")


class CanvasSnapshot(Base):
    __tablename__ = "canvas_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"))
    snapshot: Mapped[dict] = mapped_column(JSON)  # Full Tldraw JSON
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    Index("idx_snapshots_session_id", "session_id")


class RagFile(Base):
    __tablename__ = "rag_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(256))
    file_type: Mapped[str] = mapped_column(String(32))  # pdf/docx/txt
    file_path: Mapped[str] = mapped_column(String(512))  # Storage path
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/processing/completed/failed
    vector_ids: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)  # pgvector IDs
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship()
    session: Mapped["Session"] = relationship()

    Index("idx_rag_files_user_id", "user_id")
    Index("idx_rag_files_session_id", "session_id")


class FeishuBitableConfig(Base):
    __tablename__ = "feishu_bitable_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    app_token: Mapped[str] = mapped_column(String(128))
    table_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship()
