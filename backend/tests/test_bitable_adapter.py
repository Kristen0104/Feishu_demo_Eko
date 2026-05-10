from __future__ import annotations

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.modules.bitable.cli_adapter import BitableCliAdapter, BitableCliError


class _Process:
    def __init__(self, *, returncode: int, stdout: bytes = b"{}", stderr: bytes = b"") -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


class BitableCliAdapterTest(IsolatedAsyncioTestCase):
    async def test_list_fields_parses_json_output(self) -> None:
        process = _Process(returncode=0, stdout=b'{"items":[{"field_name":"Title"}]}')
        with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)) as create:
            result = await BitableCliAdapter(binary="lark-cli", timeout_seconds=1).list_fields("app_token", "tbl_test")

        self.assertEqual(result["items"][0]["field_name"], "Title")
        args = create.call_args.args
        self.assertIn("--jq", args)
        self.assertIn(".", args)
        self.assertIn("--as", args)
        self.assertIn("user", args)

    async def test_non_zero_exit_raises_bitable_error(self) -> None:
        process = _Process(returncode=2, stderr=b"permission denied app_secret baseabc")
        with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
            with self.assertRaises(BitableCliError) as ctx:
                await BitableCliAdapter(binary="lark-cli", timeout_seconds=1).list_fields("secret", "tbl_test")

        self.assertEqual(ctx.exception.returncode, 2)
        self.assertIn("permission denied", str(ctx.exception))
        self.assertNotIn("app_secret", str(ctx.exception))
        self.assertNotIn("baseabc", str(ctx.exception))
        self.assertNotIn("secret", " ".join(ctx.exception.command))

    async def test_timeout_raises_bitable_error(self) -> None:
        process = _Process(returncode=0)

        async def raise_timeout(awaitable, timeout):  # noqa: ANN001
            awaitable.close()
            raise asyncio.TimeoutError

        with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
            with patch("asyncio.wait_for", new=raise_timeout):
                with self.assertRaises(BitableCliError):
                    await BitableCliAdapter(binary="lark-cli", timeout_seconds=1).list_fields("secret", "tbl_test")

        self.assertTrue(process.killed)
