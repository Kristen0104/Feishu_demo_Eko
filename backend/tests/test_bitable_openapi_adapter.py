from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from app.modules.bitable.openapi_adapter import BitableOpenApiAdapter, BitableOpenApiError


class _FeishuClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def request_openapi_json(self, method, path, *, params=None, json_body=None, headers=None):  # noqa: ANN001
        self.calls.append(
            {
                "method": method,
                "path": path,
                "params": params or {},
                "json_body": json_body,
                "headers": headers or {},
            }
        )
        if isinstance(self.payloads[0], Exception):
            raise self.payloads.pop(0)
        return self.payloads.pop(0)


class BitableOpenApiAdapterTest(IsolatedAsyncioTestCase):
    async def test_list_fields_calls_feishu_openapi(self) -> None:
        client = _FeishuClient(
            [
                {
                    "code": 0,
                    "data": {"items": [{"field_id": "fld_title", "field_name": "Title"}], "has_more": False},
                }
            ]
        )
        result = await BitableOpenApiAdapter(feishu_client=client).list_fields("app_token", "tbl_test")

        self.assertEqual(result["items"][0]["field_name"], "Title")
        self.assertEqual(client.calls[0]["method"], "GET")
        self.assertEqual(client.calls[0]["path"], "/open-apis/bitable/v1/apps/app_token/tables/tbl_test/fields")
        self.assertEqual(client.calls[0]["params"]["page_size"], 200)
        self.assertEqual(client.calls[0]["params"]["text_field_as_array"], "false")

    async def test_create_and_update_record_return_normalizer_compatible_payloads(self) -> None:
        client = _FeishuClient(
            [
                {"code": 0, "data": {"record": {"record_id": "rec_created", "fields": {"Title": "A"}}}},
                {"code": 0, "data": {"record": {"record_id": "rec_created", "fields": {"Title": "B"}}}},
            ]
        )
        adapter = BitableOpenApiAdapter(feishu_client=client)

        created = await adapter.create_record("app_token", "tbl_test", {"Title": "A"})
        updated = await adapter.update_record("app_token", "tbl_test", "rec_created", {"Title": "B"})

        self.assertEqual(created["data"]["record"]["record_id"], "rec_created")
        self.assertEqual(updated["data"]["record"]["fields"]["Title"], "B")
        self.assertEqual(client.calls[0]["method"], "POST")
        self.assertEqual(client.calls[0]["json_body"], {"fields": {"Title": "A"}})
        self.assertEqual(client.calls[1]["method"], "PUT")
        self.assertIn("/records/rec_created", client.calls[1]["path"])

    async def test_openapi_error_redacts_app_token(self) -> None:
        client = _FeishuClient([RuntimeError("permission denied for app_secret_token and baseabc")])

        with self.assertRaises(BitableOpenApiError) as ctx:
            await BitableOpenApiAdapter(feishu_client=client).list_records("app_secret_token", "tbl_test")

        self.assertIn("permission denied", str(ctx.exception))
        self.assertNotIn("app_secret_token", str(ctx.exception))
        self.assertNotIn("baseabc", str(ctx.exception))
        self.assertNotIn("app_secret_token", ctx.exception.path or "")

    async def test_api_code_error_becomes_bitable_error(self) -> None:
        client = _FeishuClient([{"code": 1254000, "msg": "invalid app_secret_token", "request_id": "req_1"}])

        with self.assertRaises(BitableOpenApiError) as ctx:
            await BitableOpenApiAdapter(feishu_client=client).list_records("app_secret_token", "tbl_test")

        self.assertEqual(ctx.exception.code, 1254000)
        self.assertEqual(ctx.exception.request_id, "req_1")
        self.assertNotIn("app_secret_token", str(ctx.exception))

    async def test_search_records_uses_record_list_fallback_shape(self) -> None:
        client = _FeishuClient(
            [
                {
                    "code": 0,
                    "data": {
                        "items": [{"record_id": "rec_1", "fields": {"Title": "Finals plan"}}],
                        "has_more": False,
                    },
                }
            ]
        )

        result = await BitableOpenApiAdapter(feishu_client=client).search_records(
            "app_token",
            "tbl_test",
            query="Finals",
            limit=3,
            search_fields=["Title"],
            select_fields=["Title", "Owner"],
        )

        self.assertEqual(result["items"][0]["record_id"], "rec_1")
        self.assertEqual(client.calls[0]["path"], "/open-apis/bitable/v1/apps/app_token/tables/tbl_test/records")
        self.assertEqual(client.calls[0]["params"]["field_names"], '["Title", "Owner"]')
