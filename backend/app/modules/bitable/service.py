from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.modules.bitable import normalizer
from app.modules.bitable.discovery import BitableBaseResolver
from app.modules.bitable.models import BitableSource
from app.modules.bitable.openapi_adapter import BitableOpenApiAdapter, BitableOpenApiError
from app.modules.bitable.repository import BitableRepository
from app.modules.bitable.schemas import (
    BitableArchiveRequest,
    BitableArchiveResponse,
    BitableArchiveResult,
    BitableInspectResult,
    BitableQueryRequest,
    BitableQueryResponse,
    BitableRecordContext,
    BitableSchemaResponse,
    BitableSourceCreate,
    BitableSourceSchema,
    BitableSourceUpdate,
)
from app.modules.feishu.identity_service import FeishuIdentityService, FeishuReauthRequired

logger = logging.getLogger(__name__)


class BitableService:
    def __init__(
        self,
        repository: BitableRepository,
        *,
        adapter: BitableOpenApiAdapter | None = None,
        base_resolver: BitableBaseResolver | None = None,
        identity_service: FeishuIdentityService | None = None,
    ) -> None:
        self._repository = repository
        self._adapter = adapter or BitableOpenApiAdapter()
        self._base_resolver = base_resolver
        self._identity_service = identity_service

    async def list_sources(self, workspace_id: str, *, created_by: str | None = None) -> list[BitableSourceSchema]:
        if created_by is not None:
            sources = await self._repository.list_owned_sources(workspace_id, created_by=created_by)
        else:
            sources = await self._repository.list_sources(workspace_id)
        return [self._source_schema(source) for source in sources]

    async def create_source(self, payload: BitableSourceCreate, *, created_by: str | None = None) -> BitableSourceSchema:
        payload = await self._resolve_create_payload(payload, created_by=created_by)
        source = await self._repository.create_source(payload, created_by=created_by)
        return self._source_schema(source)

    async def update_source(
        self,
        source_id: str,
        payload: BitableSourceUpdate,
        *,
        created_by: str | None = None,
    ) -> BitableSourceSchema:
        source = await self._require_source(source_id, created_by=created_by)
        return self._source_schema(await self._repository.update_source(source, payload))

    async def delete_source(self, source_id: str, *, created_by: str | None = None) -> None:
        source = await self._require_source(source_id, created_by=created_by)
        await self._repository.delete_source(source)

    async def inspect_source(self, source_id: str, *, created_by: str | None = None) -> BitableInspectResult:
        source = await self._require_source(source_id, created_by=created_by)
        access_token = await self._user_access_token(created_by)
        try:
            table_payload = await self._adapter.get_table(source.app_token, source.table_id, access_token=access_token)
            fields_payload = await self._adapter.list_fields(source.app_token, source.table_id, access_token=access_token)
            views_payload = await self._adapter.list_views(source.app_token, source.table_id, access_token=access_token)
            table = normalizer.extract_table(table_payload)
            fields = normalizer.normalize_fields(fields_payload) or normalizer.normalize_fields(table_payload)
            views = normalizer.normalize_views(views_payload) or normalizer.normalize_views(table_payload)
            snapshot = {"table": table, "fields": fields, "views": views}
            source = await self._repository.update_check_status(source, status="ok", snapshot=snapshot)
            return BitableInspectResult(
                source=self._source_schema(source),
                table=table,
                fields=fields,
                views=views,
                raw={"table": table_payload, "fields": fields_payload, "views": views_payload},
            )
        except BitableOpenApiError as exc:
            source = await self._repository.update_check_status(source, status="failed", error=str(exc)[:1000])
            raise

    async def get_schema(self, workspace_id: str) -> BitableSchemaResponse:
        return BitableSchemaResponse(sources=await self.list_sources(workspace_id))

    async def query_records(self, payload: BitableQueryRequest, *, created_by: str | None = None) -> BitableQueryResponse:
        if not settings.BITABLE_ENABLED:
            return BitableQueryResponse(records=[])

        sources = await self._enabled_sources(payload.workspace_id, purposes={"context", "both"}, created_by=created_by)
        records: list[BitableRecordContext] = []
        failures: list[dict[str, str]] = []
        per_source_limit = min(5, payload.limit)
        access_token = await self._user_access_token(created_by)
        for source in sources:
            try:
                records.extend(
                    await self._query_source(
                        source,
                        query=payload.query,
                        limit=per_source_limit,
                        access_token=access_token,
                    )
                )
            except BitableOpenApiError as exc:
                if access_token:
                    try:
                        records.extend(await self._query_source(source, query=payload.query, limit=per_source_limit))
                        continue
                    except Exception as fallback_exc:  # noqa: BLE001
                        logger.warning(
                            "Bitable query tenant fallback failed source=%s table=%s: %s",
                            source.id,
                            source.table_id,
                            fallback_exc,
                        )
                        failures.append({"source_id": source.id, "message": str(fallback_exc)})
                        continue
                logger.warning("Bitable query source failed source=%s table=%s: %s", source.id, source.table_id, exc)
                failures.append({"source_id": source.id, "message": str(exc)})
            except Exception as exc:  # noqa: BLE001
                logger.warning("Bitable query source failed source=%s table=%s: %s", source.id, source.table_id, exc)
                failures.append({"source_id": source.id, "message": str(exc)})
        records = sorted(records, key=lambda record: record.score, reverse=True)[: payload.limit]
        return BitableQueryResponse(records=records, failures=failures)

    async def archive_artifact(
        self,
        payload: BitableArchiveRequest,
        *,
        created_by: str | None = None,
    ) -> BitableArchiveResponse:
        if not settings.BITABLE_ENABLED or not settings.BITABLE_ARCHIVE_ENABLED:
            return BitableArchiveResponse(results=[])

        sources = await self._enabled_sources(payload.workspace_id, purposes={"archive", "both"}, created_by=created_by)
        results: list[BitableArchiveResult] = []
        access_token = await self._user_access_token(created_by)
        for source in sources:
            result = await self._archive_to_source(source, payload, access_token=access_token)
            if result.status == "failed" and access_token:
                result = await self._archive_to_source(source, payload, access_token=None)
            results.append(result)
        return BitableArchiveResponse(results=results)

    async def _enabled_sources(
        self,
        workspace_id: str,
        *,
        purposes: set[str],
        created_by: str | None = None,
    ) -> list[BitableSource]:
        if created_by is None:
            logger.info("Bitable source lookup skipped because created_by is missing workspace=%s", workspace_id)
            return []
        return [
            source
            for source in await self._repository.list_owned_sources(workspace_id, created_by=created_by)
            if source.enabled and source.purpose in purposes
        ]

    async def _resolve_create_payload(
        self,
        payload: BitableSourceCreate,
        *,
        created_by: str | None = None,
    ) -> BitableSourceCreate:
        base_id = self._clean_text(payload.base_id)
        app_token = self._clean_text(payload.app_token)
        if base_id and app_token:
            raise ValueError("base_id and app_token cannot both be provided")
        if not base_id and not app_token:
            raise ValueError("base_id or app_token is required")
        if base_id:
            if created_by is None:
                raise ValueError("Authenticated user is required to resolve base_id")
            if self._base_resolver is None:
                raise ValueError("Bitable base resolver is not configured")
            app_token = await self._base_resolver.resolve_base_token(base_id, user_id=created_by)
        return payload.model_copy(update={"app_token": app_token, "base_id": None})

    async def _query_source(
        self,
        source: BitableSource,
        *,
        query: str,
        limit: int,
        access_token: str | None = None,
    ) -> list[BitableRecordContext]:
        table_name = self._table_name(source)
        search_fields = await self._search_fields(source, access_token=access_token)
        select_fields = self._select_fields(source, search_fields)
        records_payload: dict[str, Any] | None = None
        if search_fields:
            try:
                records_payload = await self._adapter.search_records(
                    source.app_token,
                    source.table_id,
                    query=query,
                    view_id=source.view_id,
                    limit=limit,
                    search_fields=search_fields,
                    select_fields=select_fields,
                    access_token=access_token,
                )
            except BitableOpenApiError as exc:
                logger.info("Bitable record-search fell back to record-list source=%s: %s", source.id, exc)

        if records_payload is None:
            records_payload = await self._adapter.list_records(
                source.app_token,
                source.table_id,
                view_id=source.view_id,
                page_size=50,
                access_token=access_token,
            )
        records = normalizer.normalize_records(records_payload)
        contexts = [
            normalizer.record_to_context(source, record, query=query, table_name=table_name)
            for record in records
        ]
        return sorted(contexts, key=lambda record: record.score, reverse=True)[:limit]

    async def _archive_to_source(
        self,
        source: BitableSource,
        payload: BitableArchiveRequest,
        *,
        access_token: str | None = None,
    ) -> BitableArchiveResult:
        artifact = dict(payload.artifact)
        kind = str(artifact.get("kind") or artifact.get("artifact_kind") or "artifact")
        job_id = str(artifact.get("job_id") or artifact.get("task_id") or "") or None
        fields = normalizer.build_archive_fields(source, artifact, session_id=payload.session_id)
        if not fields:
            return BitableArchiveResult(source_id=source.id, status="skipped", message="未配置可归档字段")

        existing = await self._repository.get_archive_link(
            session_id=payload.session_id,
            artifact_kind=kind,
            source_id=source.id,
        )
        try:
            if existing is not None:
                raw = await self._adapter.update_record(
                    source.app_token,
                    source.table_id,
                    existing.record_id,
                    fields,
                    access_token=access_token,
                )
                record_id = existing.record_id
                status = "updated"
            else:
                raw = await self._adapter.create_record(
                    source.app_token,
                    source.table_id,
                    fields,
                    access_token=access_token,
                )
                record_id = normalizer.extract_record_id(raw)
                status = "created"
            if not record_id:
                raise BitableOpenApiError("Bitable OpenAPI response did not include record_id")
            record_url = await self._record_share_link(source, record_id, access_token=access_token)
            await self._repository.save_archive_link(
                session_id=payload.session_id,
                artifact_kind=kind,
                artifact_job_id=job_id,
                source_id=source.id,
                record_id=record_id,
                record_url=record_url,
                status=status,
            )
            return BitableArchiveResult(
                source_id=source.id,
                record_id=record_id,
                record_url=record_url,
                status=status,  # type: ignore[arg-type]
                message="已归档到 Bitable" if status == "created" else "已更新 Bitable 归档记录",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Archive artifact to Bitable failed source=%s session=%s: %s", source.id, payload.session_id, exc)
            if existing is not None:
                await self._repository.save_archive_link(
                    session_id=payload.session_id,
                    artifact_kind=kind,
                    artifact_job_id=job_id,
                    source_id=source.id,
                    record_id=existing.record_id,
                    record_url=existing.record_url,
                    status="failed",
                    error=str(exc)[:1000],
                )
            return BitableArchiveResult(
                source_id=source.id,
                record_id=existing.record_id if existing is not None else None,
                record_url=existing.record_url if existing is not None else None,
                status="failed",
                message="Bitable 归档失败，主任务已继续完成",
                error=str(exc),
            )

    async def _record_share_link(
        self,
        source: BitableSource,
        record_id: str,
        *,
        access_token: str | None = None,
    ) -> str | None:
        try:
            payload = await self._adapter.create_record_share_link(
                source.app_token,
                source.table_id,
                record_id,
                access_token=access_token,
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("Create Bitable record share link skipped source=%s record=%s: %s", source.id, record_id, exc)
            return None
        if payload is None:
            return None
        return normalizer.extract_share_link(payload, record_id)

    async def _search_fields(self, source: BitableSource, *, access_token: str | None = None) -> list[str]:
        configured = [
            source.title_field,
            source.summary_field,
            source.status_field,
            source.type_field,
            source.owner_field,
            source.date_field,
        ]
        fields = [field for field in configured if field]
        if fields:
            return list(dict.fromkeys(fields))[:20]

        snapshot_fields = source.last_schema_snapshot.get("fields") if isinstance(source.last_schema_snapshot, dict) else None
        if not isinstance(snapshot_fields, list) or not snapshot_fields:
            try:
                payload = await self._adapter.list_fields(source.app_token, source.table_id, access_token=access_token)
                snapshot_fields = normalizer.normalize_fields(payload)
            except Exception as exc:  # noqa: BLE001
                logger.info("Bitable list_fields for search projection failed source=%s: %s", source.id, exc)
                snapshot_fields = []
        names: list[str] = []
        for field in snapshot_fields:
            if not isinstance(field, dict):
                continue
            name = field.get("field_name") or field.get("name") or field.get("field_id")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return names[:20]

    def _select_fields(self, source: BitableSource, search_fields: list[str]) -> list[str]:
        fields = [
            source.title_field,
            source.summary_field,
            source.status_field,
            source.type_field,
            source.owner_field,
            source.date_field,
            source.url_field,
            *search_fields,
        ]
        return [field for field in dict.fromkeys(field for field in fields if field)][:50]

    def _table_name(self, source: BitableSource) -> str | None:
        snapshot = source.last_schema_snapshot if isinstance(source.last_schema_snapshot, dict) else {}
        table = snapshot.get("table") if isinstance(snapshot.get("table"), dict) else {}
        value = table.get("table_name") or table.get("name")
        return str(value) if value else None

    async def _require_source(self, source_id: str, *, created_by: str | None = None) -> BitableSource:
        source = (
            await self._repository.get_owned_source(source_id, created_by=created_by)
            if created_by is not None
            else await self._repository.get_source(source_id)
        )
        if source is None:
            raise LookupError("Bitable source not found")
        return source

    async def _user_access_token(self, created_by: str | None) -> str | None:
        if created_by is None or self._identity_service is None:
            return None
        try:
            identity = await self._identity_service.get_bound_identity(created_by)
        except FeishuReauthRequired:
            return None
        return identity.access_token if identity else None

    def _source_schema(self, source: BitableSource) -> BitableSourceSchema:
        return BitableSourceSchema(
            id=source.id,
            workspace_id=source.workspace_id,
            name=source.name,
            app_token_masked=self._mask_app_token(source.app_token),
            table_id=source.table_id,
            view_id=source.view_id,
            enabled=source.enabled,
            purpose=source.purpose,  # type: ignore[arg-type]
            title_field=source.title_field,
            summary_field=source.summary_field,
            url_field=source.url_field,
            status_field=source.status_field,
            type_field=source.type_field,
            owner_field=source.owner_field,
            date_field=source.date_field,
            field_mapping=source.field_mapping,
            last_schema_snapshot=source.last_schema_snapshot,
            last_check_status=source.last_check_status,
            last_check_error=source.last_check_error,
            created_by=source.created_by,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )

    def _mask_app_token(self, token: str | None) -> str | None:
        if not token:
            return None
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}***{token[-4:]}"

    def _clean_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
