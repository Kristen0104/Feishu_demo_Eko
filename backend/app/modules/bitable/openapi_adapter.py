from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.modules.feishu.client import FeishuClient

logger = logging.getLogger(__name__)


class BitableOpenApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        request_id: str | None = None,
        path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id
        self.path = path


@dataclass(frozen=True)
class BitableOpenApiAdapter:
    """Thin Feishu Bitable OpenAPI adapter.

    Business ownership checks live in BitableService. This layer only maps the
    existing source operations to Feishu OpenAPI and keeps app/base tokens out
    of logs and raised messages.
    """

    feishu_client: FeishuClient | None = None

    async def list_bases(self, *, access_token: str | None = None) -> dict[str, Any]:
        return await self._paged_request(
            "POST",
            "/open-apis/search/v2/doc_wiki/search",
            page_size=20,
            json_body={
                "query": "",
                "doc_filter": {"doc_types": ["BITABLE"]},
            },
            access_token=access_token,
        )

    async def get_table(self, app_token: str, table_id: str, *, access_token: str | None = None) -> dict[str, Any]:
        payload = await self.list_tables(app_token, access_token=access_token)
        items = self._items(payload)
        for item in items:
            if str(item.get("table_id") or item.get("id") or "") == table_id:
                return {"data": {"table": item}}
        return {"data": {"table": {"table_id": table_id}}}

    async def list_tables(self, app_token: str, *, access_token: str | None = None) -> dict[str, Any]:
        return await self._paged_request(
            "GET",
            f"/open-apis/bitable/v1/apps/{app_token}/tables",
            page_size=100,
            access_token=access_token,
        )

    async def get_wiki_node(self, wiki_token: str, *, access_token: str | None = None) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/open-apis/wiki/v2/spaces/get_node",
            params={"token": wiki_token},
            access_token=access_token,
        )

    async def list_fields(self, app_token: str, table_id: str, *, access_token: str | None = None) -> dict[str, Any]:
        return await self._paged_request(
            "GET",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            page_size=200,
            params={"text_field_as_array": "false"},
            access_token=access_token,
        )

    async def list_views(self, app_token: str, table_id: str, *, access_token: str | None = None) -> dict[str, Any]:
        return await self._paged_request(
            "GET",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views",
            page_size=200,
            access_token=access_token,
        )

    async def search_records(
        self,
        app_token: str,
        table_id: str,
        *,
        query: str,
        view_id: str | None = None,
        limit: int = 8,
        search_fields: list[str] | None = None,
        select_fields: list[str] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        _ = query, search_fields
        page_size = max(1, min(max(limit * 5, limit), 200))
        return await self.list_records(
            app_token,
            table_id,
            view_id=view_id,
            page_size=page_size,
            select_fields=select_fields,
            access_token=access_token,
        )

    async def list_records(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: str | None = None,
        page_size: int = 50,
        select_fields: list[str] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"text_field_as_array": "false"}
        if view_id:
            params["view_id"] = view_id
        if select_fields:
            params["field_names"] = json.dumps(select_fields[:50], ensure_ascii=False)
        return await self._paged_request(
            "GET",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            page_size=max(1, min(page_size, 200)),
            params=params,
            access_token=access_token,
        )

    async def create_record(
        self,
        app_token: str,
        table_id: str,
        fields: dict[str, Any],
        *,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params={"ignore_consistency_check": "true"},
            json_body={"fields": fields},
            access_token=access_token,
        )

    async def update_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: dict[str, Any],
        *,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            params={"ignore_consistency_check": "true"},
            json_body={"fields": fields},
            access_token=access_token,
        )

    async def create_record_share_link(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        *,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        _ = app_token, table_id, record_id, access_token
        return None

    async def _paged_request(
        self,
        method: str,
        path: str,
        *,
        page_size: int,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        merged_items: list[dict[str, Any]] = []
        last_payload: dict[str, Any] = {}
        page_token: str | None = None

        for _ in range(20):
            page_params = dict(params or {})
            page_body = dict(json_body or {})
            if method.upper() == "GET":
                page_params["page_size"] = page_size
            else:
                page_body["page_size"] = page_size
            if page_token:
                if method.upper() == "GET":
                    page_params["page_token"] = page_token
                else:
                    page_body["page_token"] = page_token
            last_payload = await self._request(
                method,
                path,
                params=page_params,
                json_body=page_body or None,
                access_token=access_token,
            )
            data = last_payload.get("data") if isinstance(last_payload.get("data"), dict) else {}
            page_items = data.get("items") or data.get("res_units") or []
            for item in page_items:
                if isinstance(item, dict):
                    merged_items.append(item)
            if not data.get("has_more") or not data.get("page_token"):
                break
            page_token = str(data["page_token"])

        data = dict(last_payload.get("data") if isinstance(last_payload.get("data"), dict) else {})
        data["items"] = merged_items
        if "res_units" in data:
            data["res_units"] = merged_items
        data["has_more"] = False
        data.pop("page_token", None)
        return {**last_payload, "data": data, "items": merged_items}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        client = self.feishu_client or FeishuClient()
        safe_path = self._redact_text(path)
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
        try:
            payload = await asyncio.to_thread(
                client.request_openapi_json,
                method,
                path,
                params=params,
                json_body=json_body,
                headers=headers,
            )
        except Exception as exc:  # noqa: BLE001
            message = self._redact_text(str(exc))
            logger.warning("Bitable OpenAPI request failed path=%s error=%s", safe_path, message)
            raise BitableOpenApiError(message, path=safe_path) from exc

        if payload.get("code", 0) != 0:
            code = payload.get("code")
            msg = self._redact_text(str(payload.get("msg") or "Bitable OpenAPI request failed"))
            request_id = payload.get("request_id")
            logger.warning("Bitable OpenAPI error path=%s code=%s request_id=%s msg=%s", safe_path, code, request_id, msg)
            raise BitableOpenApiError(
                msg,
                code=int(code) if isinstance(code, int) else None,
                request_id=str(request_id) if request_id else None,
                path=safe_path,
            )
        return payload

    def _items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        items = data.get("items") if isinstance(data, dict) else None
        return [dict(item) for item in items or [] if isinstance(item, dict)]

    def _redact_text(self, text: str) -> str:
        return re.sub(r"\b(?:app_[A-Za-z0-9_-]+|bascn[A-Za-z0-9_-]+|base[A-Za-z0-9_-]+|MAGOb[A-Za-z0-9_-]+)\b", "***", text)
