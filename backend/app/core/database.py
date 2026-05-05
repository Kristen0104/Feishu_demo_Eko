"""
数据库连接模块
管理 PostgreSQL 异步连接，使用 SQLAlchemy asyncpg 驱动
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        existing_rag_chunk_vector_type = await conn.scalar(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'rag_chunks'
                  AND a.attname = 'embedding'
                  AND NOT a.attisdropped
                """
            )
        )
        expected_rag_chunk_vector_type = f"vector({settings.RAG_EMBEDDING_DIMENSIONS})"
        if existing_rag_chunk_vector_type and existing_rag_chunk_vector_type != expected_rag_chunk_vector_type:
            await conn.execute(text("DROP TABLE rag_chunks"))
            from app.modules.rag.models import RagChunk

            await conn.run_sync(RagChunk.__table__.create)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(1024)"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email ON users (email)"))
        await conn.execute(
            text(
                """
                INSERT INTO users (id, email, name, display_name)
                VALUES ('system', NULL, 'System', 'System')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        await conn.execute(text("ALTER TABLE rag_files ADD COLUMN IF NOT EXISTS source VARCHAR(1024)"))
        await conn.execute(text("ALTER TABLE rag_files ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"))
        await conn.execute(text("ALTER TABLE rag_files ADD COLUMN IF NOT EXISTS file_metadata JSONB DEFAULT '{}'::jsonb"))
        await conn.execute(text("UPDATE rag_files SET source = COALESCE(source, file_path, filename, id) WHERE source IS NULL"))
        await conn.execute(text("UPDATE rag_files SET content_hash = COALESCE(content_hash, id) WHERE content_hash IS NULL"))
        await conn.execute(text("UPDATE rag_files SET file_metadata = '{}'::jsonb WHERE file_metadata IS NULL"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_files_source ON rag_files (source)"))


from app.modules.auth import models as _auth_models  # noqa: E402,F401
from app.modules.team import models as _team_models  # noqa: E402,F401
from app.modules.rag import models as _rag_models  # noqa: E402,F401
