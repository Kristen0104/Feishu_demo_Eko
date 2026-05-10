from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.modules.bitable.models import BitableSource
from app.modules.bitable.schemas import BitableRecordContext


def extract_items(payload: Any, *keys: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    data = payload.get("data")
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
        if isinstance(data.get("items"), list):
            return data["items"]
    if isinstance(payload.get("items"), list):
        return payload["items"]
    return []


def extract_table(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    table = data.get("table") if isinstance(data, dict) and isinstance(data.get("table"), dict) else {}
    if table:
        return table
    if isinstance(data, dict):
        return {
            key: value
            for key, value in data.items()
            if key in {"table_id", "table_name", "name", "id"} and value is not None
        }
    return {}


def normalize_fields(payload: dict[str, Any]) -> list[dict[str, Any]]:
    fields = extract_items(payload, "fields", "items")
    return [dict(item) for item in fields if isinstance(item, dict)]


def normalize_views(payload: dict[str, Any]) -> list[dict[str, Any]]:
    views = extract_items(payload, "views", "items")
    return [dict(item) for item in views if isinstance(item, dict)]


def normalize_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    items = extract_items(data, "records", "items")
    if items:
        return [dict(item) for item in items if isinstance(item, dict)]

    fields = data.get("fields") if isinstance(data, dict) and isinstance(data.get("fields"), list) else []
    record_ids = data.get("record_id_list") if isinstance(data, dict) and isinstance(data.get("record_id_list"), list) else []
    rows = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), list) else []
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, list):
            continue
        row_fields = {
            str(fields[col_index] if col_index < len(fields) else f"field_{col_index + 1}"): value
            for col_index, value in enumerate(row)
        }
        normalized.append(
            {
                "record_id": str(record_ids[index]) if index < len(record_ids) else f"row_{index + 1}",
                "fields": row_fields,
            }
        )
    return normalized


def record_to_context(
    source: BitableSource,
    record: dict[str, Any],
    *,
    query: str,
    table_name: str | None = None,
) -> BitableRecordContext:
    raw_fields = _extract_record_fields(record)
    fields = {key: _stringify_cell_value(value) for key, value in raw_fields.items()}
    title = _first_non_empty(
        fields.get(source.title_field or ""),
        record.get("title"),
        fields.get("标题"),
        fields.get("名称"),
        next(iter(fields.values()), None) if fields else None,
    ) or "Bitable 记录"
    summary = _first_non_empty(
        fields.get(source.summary_field or ""),
        fields.get("摘要"),
        fields.get("说明"),
        fields.get("描述"),
    )
    content = _format_content(source, fields, table_name=table_name)
    record_id = str(record.get("record_id") or record.get("id") or record.get("recordId") or "")
    return BitableRecordContext(
        source_id=source.id,
        source_name=source.name,
        table_id=source.table_id,
        table_name=table_name,
        record_id=record_id or title,
        title=title,
        summary=summary,
        content=content,
        fields=fields,
        raw_fields=raw_fields,
        score=score_record(query, fields, source=source),
        record_url=_first_non_empty(fields.get(source.url_field or ""), record.get("record_url"), record.get("url")),
    )


def score_record(query: str, fields: dict[str, str], *, source: BitableSource) -> float:
    needle = query.strip().lower()
    if not needle:
        return 0.5
    score = 0.0

    def has(field_name: str | None) -> bool:
        return bool(field_name and needle in str(fields.get(field_name, "")).lower())

    if has(source.title_field):
        score += 0.45
    if has(source.summary_field):
        score += 0.25
    if has(source.status_field) or has(source.owner_field) or has(source.date_field):
        score += 0.15
    if any(needle in value.lower() for value in fields.values()):
        score += 0.10
    if _looks_recent(fields.get(source.date_field or "")):
        score += 0.05
    return min(score or 0.3, 1.0)


def build_archive_fields(source: BitableSource, artifact: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    kind = str(artifact.get("kind") or artifact.get("artifact_kind") or artifact.get("type") or "artifact")
    title = str(
        artifact.get("title")
        or artifact.get("source_name")
        or artifact.get("topic")
        or f"Eko {kind} - {session_id[-16:]}"
    )
    summary = str(
        artifact.get("result_summary")
        or artifact.get("summary")
        or artifact.get("current_step")
        or "Eko 已生成产物。"
    )
    link = str(artifact.get("sharing_url") or artifact.get("download_url") or artifact.get("preview_url") or "")
    now = datetime.now().astimezone().isoformat()
    fields: dict[str, Any] = {}

    def put(field_name: str | None, value: Any) -> None:
        if field_name and value not in {None, ""}:
            fields[field_name] = value

    put(source.title_field, title)
    put(source.summary_field, summary)
    put(source.status_field, str(artifact.get("status") or "completed"))
    put(source.url_field, link)
    put(source.type_field, kind)
    put(source.date_field, now)

    mapping = source.field_mapping or {}
    for target_field, expression in mapping.items():
        if not isinstance(target_field, str) or not target_field:
            continue
        if isinstance(expression, str) and expression.startswith("artifact."):
            fields[target_field] = artifact.get(expression.split(".", 1)[1])
        elif expression == "session_id":
            fields[target_field] = session_id
        elif expression == "updated_at":
            fields[target_field] = now
        else:
            fields[target_field] = expression

    return {key: value for key, value in fields.items() if value not in {None, ""}}


def extract_record_id(payload: dict[str, Any]) -> str | None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    candidates = [
        data.get("record_id") if isinstance(data, dict) else None,
        data.get("record", {}).get("record_id") if isinstance(data, dict) and isinstance(data.get("record"), dict) else None,
        data.get("id") if isinstance(data, dict) else None,
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    records = normalize_records(payload)
    if records:
        first = records[0]
        value = first.get("record_id") or first.get("id")
        return str(value) if value else None
    return None


def extract_share_link(payload: dict[str, Any], record_id: str) -> str | None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    links = data.get("record_share_links") if isinstance(data, dict) else None
    if isinstance(links, dict):
        value = links.get(record_id)
        return str(value) if value else None
    return None


def _extract_record_fields(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("fields") or record.get("record") or {}
    if isinstance(fields, dict):
        if isinstance(fields.get("fields"), dict):
            return dict(fields["fields"])
        return dict(fields)
    return {}


def _format_content(source: BitableSource, fields: dict[str, str], *, table_name: str | None) -> str:
    priority = [
        source.owner_field,
        source.status_field,
        source.type_field,
        source.date_field,
        source.summary_field,
        source.url_field,
    ]
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for field_name in priority:
        if field_name and field_name in fields and field_name not in seen:
            ordered.append((field_name, fields[field_name]))
            seen.add(field_name)
    for key, value in fields.items():
        if key not in seen:
            ordered.append((key, value))
            seen.add(key)
    lines = []
    if table_name:
        lines.append(f"表：{table_name}")
    lines.extend(f"{key}：{value}" for key, value in ordered[:20] if value)
    return "\n".join(lines)


def _stringify_cell_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int | float | bool):
        return str(value)
    if isinstance(value, list):
        parts = [_stringify_cell_value(item) for item in value]
        return "、".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("text", "name", "title", "value", "display_name", "url", "link", "id"):
            candidate = value.get(key)
            if candidate not in {None, ""}:
                return _stringify_cell_value(candidate)
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _looks_recent(value: str | None) -> bool:
    if not value:
        return False
    return any(marker in value for marker in ("2026", "2025", "今天", "本周", "最近"))
