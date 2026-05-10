from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

from fastapi.routing import APIRoute

from app.config import Settings
from app.core.security import get_auth_context
from app.modules.bitable.discovery import BitableBaseResolver, BitableDiscoveryCache, BitableDiscoveryService
from app.modules.bitable.router import router
from app.modules.bitable.schemas import BitableSourceCreate
from app.modules.bitable.service import BitableService
from app.modules.feishu.identity_service import FeishuBoundIdentity, FeishuReauthRequired


class _IdentityService:
    def __init__(self, identity=None, *, reauth: bool = False):  # noqa: ANN001
        self.identity = identity
        self.reauth = reauth

    async def get_bound_identity(self, user_id):  # noqa: ANN001
        if self.reauth:
            raise FeishuReauthRequired("请重新绑定飞书账号")
        return self.identity


class _Repository:
    def __init__(self) -> None:
        self.sources = []

    async def create_source(self, payload, *, created_by=None):  # noqa: ANN001
        source = SimpleNamespace(**payload.model_dump())
        source.id = "bs_test"
        source.enabled = True
        source.last_schema_snapshot = {}
        source.last_check_status = None
        source.last_check_error = None
        source.created_by = created_by
        source.created_at = None
        source.updated_at = None
        self.sources.append(source)
        return source

    async def list_owned_sources(self, workspace_id, *, created_by):  # noqa: ANN001
        return [source for source in self.sources if source.workspace_id == workspace_id and source.created_by == created_by]

    async def get_owned_source(self, source_id, *, created_by):  # noqa: ANN001
        return next((source for source in self.sources if source.id == source_id and source.created_by == created_by), None)


class _Adapter:
    def __init__(self, *, user_bases_error: bool = False, search_payload: dict | None = None) -> None:  # noqa: ANN401
        self.calls = []
        self.user_bases_error = user_bases_error
        self.search_payload = search_payload

    async def list_bases(self, *, access_token=None):  # noqa: ANN001
        self.calls.append(("list_bases", access_token))
        if access_token and self.user_bases_error:
            from app.modules.bitable.openapi_adapter import BitableOpenApiError

            raise BitableOpenApiError("user token cannot list bases")
        if self.search_payload is not None:
            return self.search_payload
        return {
            "data": {
                "items": [
                    {
                        "token": "bascn_user_secret" if access_token else "bascn_tenant_secret",
                        "name": "决赛项目多维表格" if access_token else "应用可访问多维表格",
                        "docs_type": "bitable",
                    }
                ]
            }
        }

    async def get_wiki_node(self, wiki_token, *, access_token=None):  # noqa: ANN001
        self.calls.append(("get_wiki_node", wiki_token, access_token))
        return {"data": {"node": {"obj_type": "bitable", "obj_token": "bascn_wiki_secret"}}}

    async def list_tables(self, app_token, *, access_token=None):  # noqa: ANN001
        self.calls.append(("list_tables", app_token, access_token))
        return {"data": {"items": [{"table_id": "tbl_project", "name": "项目排期"}]}}

    async def list_views(self, app_token, table_id, *, access_token=None):  # noqa: ANN001
        self.calls.append(("list_views", app_token, table_id, access_token))
        return {"data": {"items": [{"view_id": "vew_all", "view_name": "全部记录", "type": "grid"}]}}

    async def list_fields(self, app_token, table_id, *, access_token=None):  # noqa: ANN001
        self.calls.append(("list_fields", app_token, table_id, access_token))
        return {"data": {"items": [{"field_id": "fld_owner", "field_name": "负责人", "type": "text"}]}}


def _settings(**overrides):  # noqa: ANN003
    values = {
        "SECRET_KEY": "test-secret",
        "FEISHU_BITABLE_APP_TOKEN": "",
        "BITABLE_PRESET_BASE_NAME": "团队预置多维表格",
    }
    values.update(overrides)
    return Settings(**values)


def _identity() -> FeishuBoundIdentity:
    return FeishuBoundIdentity(
        user_id="user_1",
        feishu_open_id="ou_1",
        feishu_union_id="on_1",
        access_token="user_access_token",
        refresh_token="refresh_token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        identity_label="张三",
    )


class BitableDiscoveryTest(IsolatedAsyncioTestCase):
    async def test_unbound_status_returns_needs_reauth(self) -> None:
        service = BitableDiscoveryService(
            _IdentityService(None),
            BitableBaseResolver(_Repository(), settings=_settings()),
            adapter=_Adapter(),
            cache=BitableDiscoveryCache(),
            settings=_settings(),
        )

        status = await service.get_status("user_1")

        self.assertFalse(status.bound)
        self.assertTrue(status.needs_reauth)
        self.assertEqual(status.message, "请先绑定飞书账号")
        self.assertEqual(status.mode, "advanced_only")

    async def test_token_expired_status_returns_reauth(self) -> None:
        app_settings = _settings(FEISHU_BITABLE_APP_TOKEN="bascn_preset_secret")
        service = BitableDiscoveryService(
            _IdentityService(reauth=True),
            BitableBaseResolver(_Repository(), settings=app_settings),
            adapter=_Adapter(),
            cache=BitableDiscoveryCache(),
            settings=app_settings,
        )

        status = await service.get_status("user_1")

        self.assertTrue(status.bound)
        self.assertTrue(status.needs_reauth)
        self.assertEqual(status.message, "请重新绑定飞书账号")
        self.assertEqual(status.mode, "preset")

    async def test_preset_base_returns_masked_token(self) -> None:
        app_settings = _settings(FEISHU_BITABLE_APP_TOKEN="bascn_preset_secret")
        resolver = BitableBaseResolver(_Repository(), settings=app_settings)
        service = BitableDiscoveryService(
            _IdentityService(None),
            resolver,
            adapter=_Adapter(),
            cache=BitableDiscoveryCache(),
            settings=app_settings,
        )

        bases = await service.list_bases("user_1")

        self.assertEqual(len(bases), 1)
        self.assertEqual(bases[0].source, "preset")
        self.assertEqual(bases[0].id, resolver.preset_base_id())
        self.assertEqual(bases[0].app_token_masked, "basc***cret")
        self.assertNotIn("bascn_preset_secret", bases[0].model_dump_json())

    async def test_user_base_returns_safe_id_and_resolves_for_owner(self) -> None:
        cache = BitableDiscoveryCache()
        adapter = _Adapter()
        repository = _Repository()
        resolver = BitableBaseResolver(repository, cache=cache, settings=_settings())
        service = BitableDiscoveryService(
            _IdentityService(_identity()),
            resolver,
            adapter=adapter,
            cache=cache,
            settings=_settings(),
        )

        bases = await service.list_bases("user_1")
        base = bases[0]
        token = await resolver.resolve_base_token(base.id, user_id="user_1")

        self.assertTrue(base.id.startswith("bb_"))
        self.assertNotEqual(base.id, "bascn_user_secret")
        self.assertEqual(base.name, "决赛项目多维表格")
        self.assertEqual(token, "bascn_user_secret")
        self.assertEqual(base.app_token_masked, "basc***cret")
        self.assertNotIn("bascn_user_secret", base.model_dump_json())

    async def test_user_base_parses_official_search_result_units(self) -> None:
        cache = BitableDiscoveryCache()
        adapter = _Adapter(
            search_payload={
                "data": {
                    "res_units": [
                        {
                            "title_highlighted": "<em>决赛项目</em>",
                            "url": "https://example.feishu.cn/base/bascn_from_url?table=tbl_1",
                            "result_meta": {"doc_types": ["BITABLE"]},
                        }
                    ]
                }
            }
        )
        repository = _Repository()
        resolver = BitableBaseResolver(repository, cache=cache, settings=_settings())
        service = BitableDiscoveryService(
            _IdentityService(_identity()),
            resolver,
            adapter=adapter,
            cache=cache,
            settings=_settings(),
        )

        bases = await service.list_bases("user_1")

        self.assertEqual(len(bases), 1)
        self.assertEqual(bases[0].name, "<em>决赛项目</em>")
        self.assertEqual(await resolver.resolve_base_token(bases[0].id, user_id="user_1"), "bascn_from_url")

    async def test_resolve_base_url_accepts_pasted_token_text(self) -> None:
        cache = BitableDiscoveryCache()
        adapter = _Adapter()
        repository = _Repository()
        resolver = BitableBaseResolver(repository, cache=cache, settings=_settings())
        service = BitableDiscoveryService(
            _IdentityService(_identity()),
            resolver,
            adapter=adapter,
            cache=cache,
            settings=_settings(),
        )

        result = await service.resolve_base_url(
            "user_1",
            "项目表 bascn_manual_secret table=tbl_project view=vew_all",
        )

        self.assertEqual(result.table_id, "tbl_project")
        self.assertEqual(result.view_id, "vew_all")
        self.assertEqual(await resolver.resolve_base_token(result.base.id, user_id="user_1"), "bascn_manual_secret")
        self.assertIn(("list_tables", "bascn_manual_secret", None), adapter.calls)

    async def test_resolve_base_url_accepts_wiki_bitable_link(self) -> None:
        cache = BitableDiscoveryCache()
        adapter = _Adapter()
        repository = _Repository()
        resolver = BitableBaseResolver(repository, cache=cache, settings=_settings())
        service = BitableDiscoveryService(
            _IdentityService(_identity()),
            resolver,
            adapter=adapter,
            cache=cache,
            settings=_settings(),
        )

        result = await service.resolve_base_url("user_1", "https://example.feishu.cn/wiki/wikcnabc123")

        self.assertEqual(await resolver.resolve_base_token(result.base.id, user_id="user_1"), "bascn_wiki_secret")
        self.assertIn(("get_wiki_node", "wikcnabc123", None), adapter.calls)
        self.assertIn(("list_tables", "bascn_wiki_secret", None), adapter.calls)

    async def test_bound_user_falls_back_to_tenant_app_bases_when_user_discovery_fails(self) -> None:
        cache = BitableDiscoveryCache()
        adapter = _Adapter(user_bases_error=True)
        repository = _Repository()
        resolver = BitableBaseResolver(repository, cache=cache, settings=_settings())
        service = BitableDiscoveryService(
            _IdentityService(_identity()),
            resolver,
            adapter=adapter,
            cache=cache,
            settings=_settings(),
        )

        bases = await service.list_bases("user_1")

        self.assertEqual(len(bases), 1)
        self.assertEqual(bases[0].source, "tenant_app")
        self.assertEqual(bases[0].name, "应用可访问多维表格")
        self.assertEqual(await resolver.resolve_base_token(bases[0].id, user_id="user_1"), "bascn_tenant_secret")
        self.assertIn(("list_bases", "user_access_token"), adapter.calls)
        self.assertIn(("list_bases", None), adapter.calls)

    async def test_user_a_cannot_resolve_user_b_base_id(self) -> None:
        cache = BitableDiscoveryCache()
        base = cache.remember(
            user_id="user_a",
            app_token="bascn_user_a_secret",
            name="A 的表",
            source="user_oauth",
        )
        resolver = BitableBaseResolver(_Repository(), cache=cache, settings=_settings())

        with self.assertRaises(LookupError):
            await resolver.resolve_base_token(base.id, user_id="user_b")

    async def test_tables_views_fields_call_adapter_with_resolved_user_token(self) -> None:
        cache = BitableDiscoveryCache()
        adapter = _Adapter()
        repository = _Repository()
        resolver = BitableBaseResolver(repository, cache=cache, settings=_settings())
        service = BitableDiscoveryService(
            _IdentityService(_identity()),
            resolver,
            adapter=adapter,
            cache=cache,
            settings=_settings(),
        )
        base = (await service.list_bases("user_1"))[0]

        tables = await service.list_tables("user_1", base.id)
        views = await service.list_views("user_1", base.id, "tbl_project")
        fields = await service.list_fields("user_1", base.id, "tbl_project")

        self.assertEqual(tables[0].id, "tbl_project")
        self.assertEqual(views[0].id, "vew_all")
        self.assertEqual(fields[0].name, "负责人")
        self.assertIn(("list_tables", "bascn_user_secret", "user_access_token"), adapter.calls)
        self.assertIn(("list_views", "bascn_user_secret", "tbl_project", "user_access_token"), adapter.calls)
        self.assertIn(("list_fields", "bascn_user_secret", "tbl_project", "user_access_token"), adapter.calls)

    async def test_create_source_with_base_id_resolves_app_token(self) -> None:
        cache = BitableDiscoveryCache()
        repository = _Repository()
        base = cache.remember(
            user_id="user_1",
            app_token="bascn_user_secret",
            name="项目表",
            source="user_oauth",
        )
        service = BitableService(
            repository,
            adapter=_Adapter(),
            base_resolver=BitableBaseResolver(repository, cache=cache, settings=_settings()),
        )

        source = await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="项目表",
                base_id=base.id,
                table_id="tbl_project",
                view_id="vew_all",
                title_field="标题",
            ),
            created_by="user_1",
        )

        self.assertEqual(repository.sources[0].app_token, "bascn_user_secret")
        self.assertEqual(source.app_token_masked, "basc***cret")
        self.assertFalse(hasattr(source, "app_token"))

    async def test_create_source_without_base_id_or_app_token_returns_error(self) -> None:
        service = BitableService(
            _Repository(),
            adapter=_Adapter(),
            base_resolver=BitableBaseResolver(_Repository(), settings=_settings()),
        )

        with self.assertRaises(ValueError):
            await service.create_source(
                BitableSourceCreate(
                    workspace_id="Feishu_demo_Eko",
                    name="项目表",
                    table_id="tbl_project",
                ),
                created_by="user_1",
            )

    async def test_create_source_rejects_ambiguous_base_and_app_token(self) -> None:
        service = BitableService(
            _Repository(),
            adapter=_Adapter(),
            base_resolver=BitableBaseResolver(_Repository(), settings=_settings()),
        )

        with self.assertRaises(ValueError):
            await service.create_source(
                BitableSourceCreate(
                    workspace_id="Feishu_demo_Eko",
                    name="项目表",
                    base_id="bb_test",
                    app_token="bascn_user_secret",
                    table_id="tbl_project",
                ),
                created_by="user_1",
            )


def test_discovery_routes_require_auth() -> None:
    routes = [route for route in router.routes if isinstance(route, APIRoute) and route.path.startswith("/discovery")]

    assert routes
    for route in routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_auth_context in dependency_calls, route.path
