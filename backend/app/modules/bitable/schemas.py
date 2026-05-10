from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


BitablePurpose = Literal["context", "archive", "both"]
ArchiveStatus = Literal["created", "updated", "skipped", "failed"]


class BitableSourceBase(BaseModel):
    workspace_id: str = "Feishu_demo_Eko"
    name: str
    app_token: str
    table_id: str
    view_id: str | None = None
    purpose: BitablePurpose = "both"
    title_field: str | None = None
    summary_field: str | None = None
    url_field: str | None = None
    status_field: str | None = None
    type_field: str | None = None
    owner_field: str | None = None
    date_field: str | None = None
    field_mapping: dict[str, Any] = Field(default_factory=dict)


class BitableSourceCreate(BitableSourceBase):
    pass


class BitableSourceUpdate(BaseModel):
    name: str | None = None
    app_token: str | None = None
    view_id: str | None = None
    enabled: bool | None = None
    purpose: BitablePurpose | None = None
    title_field: str | None = None
    summary_field: str | None = None
    url_field: str | None = None
    status_field: str | None = None
    type_field: str | None = None
    owner_field: str | None = None
    date_field: str | None = None
    field_mapping: dict[str, Any] | None = None


class BitableSourceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str = "Feishu_demo_Eko"
    name: str
    app_token_masked: str | None = None
    table_id: str
    view_id: str | None = None
    enabled: bool = True
    purpose: BitablePurpose = "both"
    title_field: str | None = None
    summary_field: str | None = None
    url_field: str | None = None
    status_field: str | None = None
    type_field: str | None = None
    owner_field: str | None = None
    date_field: str | None = None
    field_mapping: dict[str, Any] = Field(default_factory=dict)
    last_schema_snapshot: dict[str, Any] = Field(default_factory=dict)
    last_check_status: str | None = None
    last_check_error: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BitableInspectResult(BaseModel):
    source: BitableSourceSchema
    table: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)
    views: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class BitableRecordContext(BaseModel):
    source_id: str
    source_name: str
    source_type: Literal["bitable"] = "bitable"
    table_id: str
    table_name: str | None = None
    record_id: str
    title: str
    summary: str | None = None
    content: str
    fields: dict[str, Any]
    raw_fields: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    record_url: str | None = None


class BitableQueryRequest(BaseModel):
    workspace_id: str = "Feishu_demo_Eko"
    query: str
    limit: int = Field(default=8, ge=1, le=20)


class BitableQueryResponse(BaseModel):
    records: list[BitableRecordContext] = Field(default_factory=list)
    failures: list[dict[str, str]] = Field(default_factory=list)


class BitableArchiveRequest(BaseModel):
    workspace_id: str = "Feishu_demo_Eko"
    session_id: str
    artifact: dict[str, Any]


class BitableArchiveResult(BaseModel):
    source_id: str
    record_id: str | None = None
    record_url: str | None = None
    status: ArchiveStatus
    message: str
    error: str | None = None


class BitableArchiveResponse(BaseModel):
    results: list[BitableArchiveResult] = Field(default_factory=list)


class BitableSchemaResponse(BaseModel):
    sources: list[BitableSourceSchema] = Field(default_factory=list)
