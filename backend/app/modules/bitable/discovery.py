from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from hmac import compare_digest
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from app.config import Settings, get_settings
from app.modules.bitable import normalizer
from app.modules.bitable.openapi_adapter import BitableOpenApiAdapter, BitableOpenApiError
from app.modules.bitable.repository import BitableRepository
from app.modules.bitable.schemas import (
    BitableBaseOption,
    BitableBaseUrlResolveResponse,
    BitableDiscoveryStatus,
    BitableFieldOption,
    BitableTableOption,
    BitableViewOption,
)
from app.modules.feishu.identity_service import FeishuIdentityService, FeishuReauthRequired

BitableBaseSource = Literal["user_oauth", "tenant_app", "preset"]


@dataclass(slots=True)
class BitableDiscoveredBase:
    id: str
    user_id: str
    app_token: str
    name: str
    source: BitableBaseSource
    expires_at: float


@dataclass(slots=True)
class ResolvedBitableBase:
    app_token: str
    source: BitableBaseSource | Literal["saved_source", "advanced"]
    name: str | None = None


class BitableDiscoveryCache:
    def __init__(self, *, ttl_seconds: int = 900) -> None:
        self._ttl_seconds = ttl_seconds
        self._items: dict[str, BitableDiscoveredBase] = {}

    def remember(
        self,
        *,
        user_id: str,
        app_token: str,
        name: str,
        source: BitableBaseSource,
    ) -> BitableDiscoveredBase:
        self._cleanup()
        base_id = f"bb_{secrets.token_urlsafe(24)}"
        item = BitableDiscoveredBase(
            id=base_id,
            user_id=user_id,
            app_token=app_token,
            name=name,
            source=source,
            expires_at=time.time() + self._ttl_seconds,
        )
        self._items[base_id] = item
        return item

    def get(self, base_id: str, *, user_id: str) -> BitableDiscoveredBase | None:
        item = self._items.get(base_id)
        if item is None:
            return None
        if item.expires_at <= time.time():
            self._items.pop(base_id, None)
            return None
        if item.user_id != user_id:
            return None
        return item

    def _cleanup(self) -> None:
        now = time.time()
        for base_id, item in list(self._items.items()):
            if item.expires_at <= now:
                self._items.pop(base_id, None)


DISCOVERY_CACHE = BitableDiscoveryCache()


class BitableBaseResolver:
    def __init__(
        self,
        repository: BitableRepository,
        *,
        cache: BitableDiscoveryCache | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._cache = cache or DISCOVERY_CACHE
        self._settings = settings or get_settings()

    async def resolve_base_token(self, base_id: str, *, user_id: str) -> str:
        return (await self.resolve_base(base_id, user_id=user_id)).app_token

    async def resolve_base(self, base_id: str, *, user_id: str) -> ResolvedBitableBase:
        cached = self._cache.get(base_id, user_id=user_id)
        if cached is not None:
            return ResolvedBitableBase(app_token=cached.app_token, source=cached.source, name=cached.name)

        source = await self._repository.get_owned_source(base_id, created_by=user_id)
        if source is not None:
            return ResolvedBitableBase(app_token=source.app_token, source="saved_source", name=source.name)

        if self._preset_app_token and compare_digest(base_id, self.preset_base_id()):
            return ResolvedBitableBase(
                app_token=self._preset_app_token,
                source="preset",
                name=self._preset_name,
            )

        raise LookupError("Bitable base not found")

    def preset_base_id(self) -> str:
        token = self._preset_app_token
        if not token:
            return "preset_unconfigured"
        import hashlib
        import hmac

        signature = hmac.new(
            str(self._settings.SECRET_KEY).encode("utf-8"),
            token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:24]
        return f"preset_{signature}"

    @property
    def _preset_app_token(self) -> str:
        return str(getattr(self._settings, "FEISHU_BITABLE_APP_TOKEN", "") or "").strip()

    @property
    def _preset_name(self) -> str:
        return str(getattr(self._settings, "BITABLE_PRESET_BASE_NAME", "") or "团队预置多维表格")


class BitableDiscoveryService:
    def __init__(
        self,
        identity_service: FeishuIdentityService,
        resolver: BitableBaseResolver,
        *,
        adapter: BitableOpenApiAdapter | None = None,
        cache: BitableDiscoveryCache | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._identity_service = identity_service
        self._resolver = resolver
        self._adapter = adapter or BitableOpenApiAdapter()
        self._cache = cache or DISCOVERY_CACHE
        self._settings = settings or get_settings()

    async def get_status(self, user_id: str) -> BitableDiscoveryStatus:
        try:
            identity = await self._identity_service.get_bound_identity(user_id)
        except FeishuReauthRequired:
            return BitableDiscoveryStatus(
                bound=True,
                needs_reauth=True,
                mode="preset" if self._has_preset else "advanced_only",
                message="请重新绑定飞书账号",
            )
        if identity is None:
            return BitableDiscoveryStatus(
                bound=False,
                needs_reauth=True,
                mode="advanced_only",
                message="请先绑定飞书账号",
            )
        mode = "user_oauth" if identity.access_token else ("preset" if self._has_preset else "tenant_app")
        return BitableDiscoveryStatus(
            bound=True,
            needs_reauth=False,
            identity_label=identity.identity_label,
            mode=mode,  # type: ignore[arg-type]
        )

    async def list_bases(self, user_id: str) -> list[BitableBaseOption]:
        bases: list[BitableBaseOption] = []
        try:
            identity = await self._identity_service.get_bound_identity(user_id)
        except FeishuReauthRequired:
            identity = None

        if identity and identity.access_token:
            try:
                payload = await self._adapter.list_bases(access_token=identity.access_token)
                bases.extend(self._base_options_from_payload(user_id, payload, source="user_oauth"))
            except BitableOpenApiError:
                bases = []

        if identity and not bases:
            try:
                payload = await self._adapter.list_bases(access_token=None)
                bases.extend(self._base_options_from_payload(user_id, payload, source="tenant_app"))
            except BitableOpenApiError:
                bases = []

        if not bases and self._has_preset:
            bases.append(self._preset_base_option())

        return bases

    async def resolve_base_url(self, user_id: str, url: str) -> BitableBaseUrlResolveResponse:
        parsed = self._parse_base_url(url)
        app_token = parsed["app_token"]
        if app_token is None and parsed["wiki_token"] is not None:
            wiki_payload = await self._adapter.get_wiki_node(parsed["wiki_token"], access_token=None)
            app_token = self._app_token_from_wiki_payload(wiki_payload)
        if app_token is None:
            raise ValueError("没有识别到多维表格 token。请粘贴飞书多维表格链接、知识库里的多维表格链接，或 bascn... token。")
        table_id = parsed.get("table_id")
        view_id = parsed.get("view_id")

        # Verify that the current Feishu app can access the base. This keeps
        # link binding product-friendly without turning it into raw token entry.
        payload = await self._adapter.list_tables(app_token, access_token=None)
        tables = self._table_options_from_payload(payload)
        name = "飞书多维表格"
        cached = self._cache.remember(user_id=user_id, app_token=app_token, name=name, source="tenant_app")
        return BitableBaseUrlResolveResponse(
            base=BitableBaseOption(
                id=cached.id,
                name=name,
                source="tenant_app",
                app_token_masked=self._mask_app_token(app_token),
            ),
            table_id=table_id if any(table.id == table_id for table in tables) else table_id,
            view_id=view_id,
        )

    async def list_tables(self, user_id: str, base_id: str) -> list[BitableTableOption]:
        resolved = await self._resolver.resolve_base(base_id, user_id=user_id)
        access_token = await self._access_token_for_resolved(user_id, resolved)
        payload = await self._adapter.list_tables(resolved.app_token, access_token=access_token)
        return self._table_options_from_payload(payload)

    async def list_views(self, user_id: str, base_id: str, table_id: str) -> list[BitableViewOption]:
        resolved = await self._resolver.resolve_base(base_id, user_id=user_id)
        access_token = await self._access_token_for_resolved(user_id, resolved)
        payload = await self._adapter.list_views(resolved.app_token, table_id, access_token=access_token)
        return self._view_options_from_payload(payload)

    async def list_fields(self, user_id: str, base_id: str, table_id: str) -> list[BitableFieldOption]:
        resolved = await self._resolver.resolve_base(base_id, user_id=user_id)
        access_token = await self._access_token_for_resolved(user_id, resolved)
        payload = await self._adapter.list_fields(resolved.app_token, table_id, access_token=access_token)
        return self._field_options_from_payload(payload)

    async def _access_token_for_resolved(self, user_id: str, resolved: ResolvedBitableBase) -> str | None:
        if resolved.source != "user_oauth":
            return None
        try:
            identity = await self._identity_service.get_bound_identity(user_id)
        except FeishuReauthRequired:
            return None
        return identity.access_token if identity else None

    def _base_options_from_payload(
        self,
        user_id: str,
        payload: dict[str, Any],
        *,
        source: BitableBaseSource,
    ) -> list[BitableBaseOption]:
        options: list[BitableBaseOption] = []
        for item in normalizer.extract_items(payload, "res_units", "files", "items"):
            if not isinstance(item, dict):
                continue
            app_token = self._first_text(
                item.get("app_token"),
                item.get("token"),
                item.get("docs_token"),
                item.get("file_token"),
                item.get("obj_token"),
                item.get("entity_id"),
                self._base_token_from_url(self._first_text(item.get("url"), item.get("docs_url"))),
            )
            if not app_token:
                continue
            result_meta = item.get("result_meta") if isinstance(item.get("result_meta"), dict) else {}
            docs_type = self._first_text(
                item.get("type"),
                item.get("file_type"),
                item.get("docs_type"),
                item.get("entity_type"),
                result_meta.get("doc_types") if result_meta else None,
            )
            if docs_type and "bitable" not in docs_type.lower() and "base" not in docs_type.lower():
                continue
            name = self._first_text(item.get("name"), item.get("title"), item.get("title_highlighted")) or "未命名多维表格"
            cached = self._cache.remember(user_id=user_id, app_token=app_token, name=name, source=source)
            options.append(
                BitableBaseOption(
                    id=cached.id,
                    name=name,
                    source=source,
                    app_token_masked=self._mask_app_token(app_token),
                )
            )
        return options

    def _table_options_from_payload(self, payload: dict[str, Any]) -> list[BitableTableOption]:
        options: list[BitableTableOption] = []
        for item in normalizer.extract_items(payload, "tables", "items"):
            if not isinstance(item, dict):
                continue
            table_id = self._first_text(item.get("table_id"), item.get("id"))
            if table_id:
                options.append(
                    BitableTableOption(
                        id=table_id,
                        name=self._first_text(item.get("name"), item.get("table_name")) or table_id,
                    )
                )
        return options

    def _view_options_from_payload(self, payload: dict[str, Any]) -> list[BitableViewOption]:
        options: list[BitableViewOption] = []
        for item in normalizer.extract_items(payload, "views", "items"):
            if not isinstance(item, dict):
                continue
            view_id = self._first_text(item.get("view_id"), item.get("id"))
            if view_id:
                options.append(
                    BitableViewOption(
                        id=view_id,
                        name=self._first_text(item.get("name"), item.get("view_name")) or view_id,
                        type=self._first_text(item.get("type"), item.get("view_type")),
                    )
                )
        return options

    def _field_options_from_payload(self, payload: dict[str, Any]) -> list[BitableFieldOption]:
        options: list[BitableFieldOption] = []
        for item in normalizer.extract_items(payload, "fields", "items"):
            if not isinstance(item, dict):
                continue
            name = self._first_text(item.get("name"), item.get("field_name"), item.get("field_id"))
            if name:
                options.append(
                    BitableFieldOption(
                        id=self._first_text(item.get("field_id"), item.get("id")),
                        name=name,
                        type=self._first_text(item.get("type"), item.get("ui_type")),
                    )
                )
        return options

    def _preset_base_option(self) -> BitableBaseOption:
        token = str(getattr(self._settings, "FEISHU_BITABLE_APP_TOKEN", "") or "")
        return BitableBaseOption(
            id=self._resolver.preset_base_id(),
            name=str(getattr(self._settings, "BITABLE_PRESET_BASE_NAME", "") or "团队预置多维表格"),
            source="preset",
            app_token_masked=self._mask_app_token(token),
        )

    @property
    def _has_preset(self) -> bool:
        return bool(str(getattr(self._settings, "FEISHU_BITABLE_APP_TOKEN", "") or "").strip())

    def _mask_app_token(self, token: str | None) -> str | None:
        if not token:
            return None
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}***{token[-4:]}"

    def _first_text(self, *values: Any) -> str | None:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _base_token_from_url(self, url: str | None) -> str | None:
        if not url:
            return None
        import re

        text = str(url).strip()
        patterns = [
            r"/base/([A-Za-z0-9_-]+)",
            r"[?&#](?:app_token|base_token|token)=([A-Za-z0-9_-]+)",
            r"\b(bascn[A-Za-z0-9_-]+)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _parse_base_url(self, url: str) -> dict[str, str | None]:
        text = str(url or "").strip()
        app_token = self._base_token_from_url(text)
        wiki_token = self._wiki_token_from_url(text)

        parsed = urlparse(text)
        query = parse_qs(parsed.query)
        table_id = self._first_text(
            *(query.get("table") or []),
            *(query.get("table_id") or []),
            *(query.get("tableId") or []),
            *self._regex_values(r"\b(tbl[A-Za-z0-9_-]+)\b", text),
        )
        view_id = self._first_text(
            *(query.get("view") or []),
            *(query.get("view_id") or []),
            *(query.get("viewId") or []),
            *self._regex_values(r"\b(vew[A-Za-z0-9_-]+)\b", text),
        )
        return {"app_token": app_token, "wiki_token": wiki_token, "table_id": table_id, "view_id": view_id}

    def _regex_values(self, pattern: str, text: str) -> list[str]:
        import re

        return [match.group(1) for match in re.finditer(pattern, text)]

    def _wiki_token_from_url(self, url: str | None) -> str | None:
        if not url:
            return None
        import re

        text = str(url).strip()
        match = re.search(r"/wiki/([A-Za-z0-9_-]+)", text)
        if match:
            return match.group(1)
        return None

    def _app_token_from_wiki_payload(self, payload: dict[str, Any]) -> str | None:
        node = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if isinstance(node.get("node"), dict):
            node = node["node"]
        obj_type = self._first_text(node.get("obj_type"), node.get("type"))
        if obj_type and "bitable" not in obj_type.lower() and "base" not in obj_type.lower():
            raise ValueError("这个 wiki 链接不是多维表格节点")
        return self._first_text(node.get("obj_token"), node.get("token"), node.get("app_token"))
