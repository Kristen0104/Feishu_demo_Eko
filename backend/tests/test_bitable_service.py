from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from app.modules.bitable.service import BitableService
from app.modules.bitable.schemas import BitableArchiveRequest, BitableQueryRequest, BitableSourceCreate


class _Repository:
    def __init__(self) -> None:
        self.sources = []
        self.archive_link = None
        self.saved_links = []

    async def create_source(self, payload, *, created_by=None):  # noqa: ANN001
        source = type("Source", (), payload.model_dump())()
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

    async def list_sources(self, workspace_id):  # noqa: ANN001
        return [source for source in self.sources if source.workspace_id == workspace_id]

    async def list_owned_sources(self, workspace_id, *, created_by):  # noqa: ANN001
        return [source for source in self.sources if source.workspace_id == workspace_id and source.created_by == created_by]

    async def list_enabled_sources(self, workspace_id, *, purposes):  # noqa: ANN001
        return [source for source in self.sources if source.workspace_id == workspace_id and source.enabled and source.purpose in purposes]

    async def get_source(self, source_id):  # noqa: ANN001
        return next((source for source in self.sources if source.id == source_id), None)

    async def get_owned_source(self, source_id, *, created_by):  # noqa: ANN001
        return next((source for source in self.sources if source.id == source_id and source.created_by == created_by), None)

    async def get_archive_link(self, *, session_id, artifact_kind, source_id):  # noqa: ANN001
        return self.archive_link

    async def save_archive_link(self, **kwargs):  # noqa: ANN003
        self.saved_links.append(kwargs)
        self.archive_link = type("ArchiveLink", (), kwargs)()
        return self.archive_link


class _Cli:
    async def list_fields(self, app_token, table_id):  # noqa: ANN001
        return {"items": [{"field_name": "标题"}, {"field_name": "负责人"}, {"field_name": "阶段"}]}

    async def search_records(self, app_token, table_id, *, query, view_id=None, limit=8, search_fields=None, select_fields=None):  # noqa: ANN001
        return {
            "items": [
                {
                    "record_id": "rec_1",
                    "fields": {"标题": "Eko 决赛开发计划", "负责人": "成员 A", "阶段": "联调"},
                }
            ]
        }

    async def create_record(self, app_token, table_id, fields):  # noqa: ANN001
        self.created_fields = fields
        return {"record": {"record_id": "rec_archive"}}

    async def update_record(self, app_token, table_id, record_id, fields):  # noqa: ANN001
        self.updated_fields = fields
        return {"record": {"record_id": record_id}}

    async def create_record_share_link(self, app_token, table_id, record_id):  # noqa: ANN001
        return {"record_share_links": {record_id: "https://example.feishu.cn/record/rec_archive"}}


class BitableServiceTest(IsolatedAsyncioTestCase):
    async def test_query_records_returns_context_records(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="项目表",
                app_token="app_test",
                table_id="tbl_test",
                title_field="标题",
                owner_field="负责人",
                status_field="阶段",
            ),
            created_by="user_1",
        )

        with patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True):
            response = await service.query_records(
                BitableQueryRequest(query="Eko 决赛开发计划", limit=5),
                created_by="user_1",
            )

        self.assertEqual(len(response.records), 1)
        self.assertEqual(response.records[0].source_type, "bitable")
        self.assertIn("负责人：成员 A", response.records[0].content)

    async def test_query_records_without_user_scope_returns_empty(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="项目表",
                app_token="app_test",
                table_id="tbl_test",
                title_field="标题",
            ),
            created_by="user_1",
        )

        with patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True):
            response = await service.query_records(BitableQueryRequest(query="Eko 决赛开发计划", limit=5))

        self.assertEqual(response.records, [])

    async def test_archive_creates_then_updates_existing_link(self) -> None:
        repository = _Repository()
        cli = _Cli()
        service = BitableService(repository, cli_adapter=cli)
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="归档表",
                app_token="app_test",
                table_id="tbl_test",
                purpose="archive",
                title_field="标题",
                url_field="链接",
                status_field="状态",
            ),
            created_by="user_1",
        )

        with (
            patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True),
            patch("app.modules.bitable.service.settings.BITABLE_ARCHIVE_ENABLED", True),
        ):
            first = await service.archive_artifact(
                BitableArchiveRequest(
                    session_id="session_1",
                    artifact={"kind": "docx", "title": "方案", "sharing_url": "https://doc", "status": "completed"},
                ),
                created_by="user_1",
            )
            second = await service.archive_artifact(
                BitableArchiveRequest(
                    session_id="session_1",
                    artifact={"kind": "docx", "title": "方案更新", "sharing_url": "https://doc2", "status": "completed"},
                ),
                created_by="user_1",
            )

        self.assertEqual(first.results[0].status, "created")
        self.assertEqual(second.results[0].status, "updated")
        self.assertEqual(repository.saved_links[-1]["record_id"], "rec_archive")

    async def test_archive_skips_when_no_archive_fields_are_configured(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="归档表",
                app_token="app_test",
                table_id="tbl_test",
                purpose="archive",
            ),
            created_by="user_1",
        )

        with (
            patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True),
            patch("app.modules.bitable.service.settings.BITABLE_ARCHIVE_ENABLED", True),
        ):
            response = await service.archive_artifact(
                BitableArchiveRequest(
                    session_id="session_1",
                    artifact={"kind": "docx", "title": "方案", "status": "completed"},
                ),
                created_by="user_1",
            )

        self.assertEqual(response.results[0].status, "skipped")
        self.assertEqual(repository.saved_links, [])

    async def test_archive_without_user_scope_returns_empty(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="归档表",
                app_token="app_test",
                table_id="tbl_test",
                purpose="archive",
                title_field="标题",
            ),
            created_by="user_1",
        )

        with (
            patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True),
            patch("app.modules.bitable.service.settings.BITABLE_ARCHIVE_ENABLED", True),
        ):
            response = await service.archive_artifact(
                BitableArchiveRequest(
                    session_id="session_1",
                    artifact={"kind": "docx", "title": "方案", "status": "completed"},
                )
            )

        self.assertEqual(response.results, [])
        self.assertEqual(repository.saved_links, [])

    async def test_source_schema_masks_app_token(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        source = await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="项目表",
                app_token="app_secret_token",
                table_id="tbl_test",
            ),
            created_by="user_1",
        )

        self.assertEqual(source.app_token_masked, "app_***oken")
        self.assertFalse(hasattr(source, "app_token"))

    async def test_user_scoped_queries_only_use_owned_sources(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="项目表",
                app_token="app_test",
                table_id="tbl_test",
                title_field="标题",
                owner_field="负责人",
                status_field="阶段",
            ),
            created_by="user_1",
        )

        with patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True):
            response = await service.query_records(
                BitableQueryRequest(query="Eko 决赛开发计划", limit=5),
                created_by="user_2",
            )

        self.assertEqual(response.records, [])

    async def test_unscoped_query_does_not_use_global_sources(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="项目表",
                app_token="app_test",
                table_id="tbl_test",
                title_field="标题",
            ),
            created_by="user_1",
        )

        with patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True):
            response = await service.query_records(BitableQueryRequest(query="Eko 决赛开发计划", limit=5))

        self.assertEqual(response.records, [])

    async def test_unscoped_archive_does_not_write_global_sources(self) -> None:
        repository = _Repository()
        service = BitableService(repository, cli_adapter=_Cli())
        await service.create_source(
            BitableSourceCreate(
                workspace_id="Feishu_demo_Eko",
                name="归档表",
                app_token="app_test",
                table_id="tbl_test",
                purpose="archive",
                title_field="标题",
            ),
            created_by="user_1",
        )

        with (
            patch("app.modules.bitable.service.settings.BITABLE_ENABLED", True),
            patch("app.modules.bitable.service.settings.BITABLE_ARCHIVE_ENABLED", True),
        ):
            response = await service.archive_artifact(
                BitableArchiveRequest(
                    session_id="session_1",
                    artifact={"kind": "docx", "title": "方案", "status": "completed"},
                )
            )

        self.assertEqual(response.results, [])
        self.assertEqual(repository.saved_links, [])
