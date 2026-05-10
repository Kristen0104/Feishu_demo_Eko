from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class BitableCliError(RuntimeError):
    def __init__(self, message: str, *, returncode: int | None = None, command: list[str] | None = None) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.command = command or []


@dataclass(frozen=True)
class BitableCliAdapter:
    binary: str | None = None
    timeout_seconds: int | None = None
    identity: str = "user"

    @property
    def _binary(self) -> str:
        return self.binary or settings.LARK_CLI_BINARY

    @property
    def _timeout(self) -> int:
        return self.timeout_seconds or settings.LARK_CLI_TIMEOUT_SECONDS

    async def list_tables(self, app_token: str) -> dict[str, Any]:
        return await self._run_base(
            "+table-list",
            "--base-token",
            app_token,
            "--offset",
            "0",
            "--limit",
            "100",
        )

    async def get_table(self, app_token: str, table_id: str) -> dict[str, Any]:
        return await self._run_base("+table-get", "--base-token", app_token, "--table-id", table_id)

    async def list_fields(self, app_token: str, table_id: str) -> dict[str, Any]:
        return await self._run_base(
            "+field-list",
            "--base-token",
            app_token,
            "--table-id",
            table_id,
            "--offset",
            "0",
            "--limit",
            "200",
        )

    async def list_views(self, app_token: str, table_id: str) -> dict[str, Any]:
        return await self._run_base(
            "+view-list",
            "--base-token",
            app_token,
            "--table-id",
            table_id,
            "--offset",
            "0",
            "--limit",
            "200",
        )

    async def list_records(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        args = [
            "+record-list",
            "--base-token",
            app_token,
            "--table-id",
            table_id,
            "--offset",
            "0",
            "--limit",
            str(max(1, min(page_size, 200))),
        ]
        if view_id:
            args.extend(["--view-id", view_id])
        return await self._run_base(*args)

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
    ) -> dict[str, Any]:
        if not search_fields:
            raise BitableCliError("record-search requires explicit search_fields")
        body: dict[str, Any] = {
            "keyword": query,
            "search_fields": search_fields[:20],
            "limit": max(1, min(limit, 200)),
            "offset": 0,
        }
        if select_fields:
            body["select_fields"] = select_fields[:50]
        if view_id:
            body["view_id"] = view_id
        return await self._run_base(
            "+record-search",
            "--base-token",
            app_token,
            "--table-id",
            table_id,
            "--json",
            json.dumps(body, ensure_ascii=False),
        )

    async def create_record(self, app_token: str, table_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._run_base(
            "+record-upsert",
            "--base-token",
            app_token,
            "--table-id",
            table_id,
            "--json",
            json.dumps(fields, ensure_ascii=False),
        )

    async def update_record(self, app_token: str, table_id: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._run_base(
            "+record-upsert",
            "--base-token",
            app_token,
            "--table-id",
            table_id,
            "--record-id",
            record_id,
            "--json",
            json.dumps(fields, ensure_ascii=False),
        )

    async def upsert_record(
        self,
        app_token: str,
        table_id: str,
        *,
        match_fields: dict[str, Any],
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        # Official +record-upsert does not match on business fields. Keep this
        # method as an adapter boundary, creating by default unless callers have
        # already resolved a record_id.
        _ = match_fields
        return await self.create_record(app_token, table_id, fields)

    async def create_record_share_link(self, app_token: str, table_id: str, record_id: str) -> dict[str, Any]:
        return await self._run_base(
            "+record-share-link-create",
            "--base-token",
            app_token,
            "--table-id",
            table_id,
            "--record-ids",
            record_id,
        )

    async def data_query(self, app_token: str, dsl: dict[str, Any]) -> dict[str, Any]:
        return await self._run_base(
            "+data-query",
            "--base-token",
            app_token,
            "--dsl",
            json.dumps(dsl, ensure_ascii=False),
        )

    async def _run_base(self, *args: str) -> dict[str, Any]:
        cmd = [self._binary, "base", *args, "--jq", ".", "--as", self.identity]
        env = dict(os.environ)
        if settings.LARK_CLI_CONFIG_DIR:
            env["LARK_CLI_CONFIG_DIR"] = settings.LARK_CLI_CONFIG_DIR
            env["LARK_CONFIG_DIR"] = settings.LARK_CLI_CONFIG_DIR
        safe_cmd = self._redact_command(cmd)
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError as exc:
            raise BitableCliError(f"Lark CLI binary not found: {self._binary}", command=safe_cmd) from exc

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self._timeout)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise BitableCliError(f"Lark CLI timed out after {self._timeout}s", command=safe_cmd) from exc

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        if process.returncode != 0:
            logger.warning("Bitable CLI failed command=%s stderr=%s", safe_cmd, self._redact_text(stderr_text))
            message = self._redact_text(stderr_text or stdout_text or "Lark CLI command failed")
            raise BitableCliError(message, returncode=process.returncode, command=safe_cmd)

        if not stdout_text:
            return {}
        try:
            parsed = json.loads(stdout_text)
        except json.JSONDecodeError as exc:
            logger.warning("Bitable CLI returned non-JSON command=%s stdout=%s", safe_cmd, self._redact_text(stdout_text[:500]))
            raise BitableCliError("Lark CLI did not return valid JSON", command=safe_cmd) from exc
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}

    def _redact_command(self, cmd: list[str]) -> list[str]:
        redacted: list[str] = []
        sensitive_next = False
        for part in cmd:
            if sensitive_next:
                redacted.append("***")
                sensitive_next = False
                continue
            redacted.append(part)
            if part in {"--base-token", "--app-token"}:
                sensitive_next = True
        return redacted

    def _redact_text(self, text: str) -> str:
        return re.sub(r"\b(?:app_[A-Za-z0-9_-]+|bascn[A-Za-z0-9_-]+|base[A-Za-z0-9_-]+|MAGOb[A-Za-z0-9_-]+)\b", "***", text)
