from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bitable.models import BitableArchiveLink, BitableSource
from app.modules.bitable.schemas import BitableSourceCreate, BitableSourceUpdate


class BitableRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_sources(self, workspace_id: str, *, created_by: str | None = None) -> list[BitableSource]:
        statement = select(BitableSource).where(BitableSource.workspace_id == workspace_id)
        if created_by is not None:
            statement = statement.where(
                or_(
                    BitableSource.created_by == created_by,
                    BitableSource.created_by.is_(None),
                )
            )
        return list(await self._session.scalars(statement.order_by(BitableSource.created_at.desc())))

    async def list_owned_sources(self, workspace_id: str, *, created_by: str) -> list[BitableSource]:
        return list(
            await self._session.scalars(
                select(BitableSource)
                .where(
                    BitableSource.workspace_id == workspace_id,
                    BitableSource.created_by == created_by,
                )
                .order_by(BitableSource.created_at.desc())
            )
        )

    async def list_enabled_sources(self, workspace_id: str, *, purposes: set[str]) -> list[BitableSource]:
        return [
            source
            for source in await self.list_sources(workspace_id)
            if source.enabled and source.purpose in purposes
        ]

    async def get_source(self, source_id: str) -> BitableSource | None:
        return await self._session.get(BitableSource, source_id)

    async def get_owned_source(self, source_id: str, *, created_by: str) -> BitableSource | None:
        return await self._session.scalar(
            select(BitableSource).where(
                BitableSource.id == source_id,
                BitableSource.created_by == created_by,
            )
        )

    async def create_source(self, payload: BitableSourceCreate, *, created_by: str | None = None) -> BitableSource:
        now = datetime.now(UTC)
        source = BitableSource(
            workspace_id=payload.workspace_id,
            name=payload.name,
            app_token=payload.app_token,
            table_id=payload.table_id,
            view_id=payload.view_id,
            enabled=True,
            purpose=payload.purpose,
            title_field=payload.title_field,
            summary_field=payload.summary_field,
            url_field=payload.url_field,
            status_field=payload.status_field,
            type_field=payload.type_field,
            owner_field=payload.owner_field,
            date_field=payload.date_field,
            field_mapping=payload.field_mapping,
            last_schema_snapshot={},
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._session.add(source)
        await self._flush_commit()
        return source

    async def update_source(self, source: BitableSource, payload: BitableSourceUpdate) -> BitableSource:
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(source, key, value)
        source.updated_at = datetime.now(UTC)
        await self._flush_commit()
        return source

    async def delete_source(self, source: BitableSource) -> None:
        await self._session.delete(source)
        await self._commit()

    async def update_check_status(
        self,
        source: BitableSource,
        *,
        status: str,
        error: str | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> BitableSource:
        source.last_check_status = status
        source.last_check_error = error
        if snapshot is not None:
            source.last_schema_snapshot = snapshot
        source.updated_at = datetime.now(UTC)
        await self._flush_commit()
        return source

    async def get_archive_link(self, *, session_id: str, artifact_kind: str, source_id: str) -> BitableArchiveLink | None:
        return await self._session.scalar(
            select(BitableArchiveLink).where(
                BitableArchiveLink.session_id == session_id,
                BitableArchiveLink.artifact_kind == artifact_kind,
                BitableArchiveLink.source_id == source_id,
            )
        )

    async def save_archive_link(
        self,
        *,
        session_id: str,
        artifact_kind: str,
        artifact_job_id: str | None,
        source_id: str,
        record_id: str,
        record_url: str | None,
        status: str,
        error: str | None = None,
    ) -> BitableArchiveLink:
        now = datetime.now(UTC)
        link = await self.get_archive_link(session_id=session_id, artifact_kind=artifact_kind, source_id=source_id)
        if link is None:
            link = BitableArchiveLink(
                session_id=session_id,
                artifact_kind=artifact_kind,
                artifact_job_id=artifact_job_id,
                source_id=source_id,
                record_id=record_id,
                record_url=record_url,
                archive_status=status,
                archive_error=error,
                created_at=now,
                updated_at=now,
            )
            self._session.add(link)
        else:
            link.artifact_job_id = artifact_job_id or link.artifact_job_id
            link.record_id = record_id
            link.record_url = record_url or link.record_url
            link.archive_status = status
            link.archive_error = error
            link.updated_at = now
        await self._flush_commit()
        return link

    async def _flush_commit(self) -> None:
        await self._session.flush()
        await self._commit()

    async def _commit(self) -> None:
        commit = getattr(self._session, "commit", None)
        if commit is not None:
            await commit()
