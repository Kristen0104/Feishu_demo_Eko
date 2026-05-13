# Bitable OpenAPI Integration

## Purpose

Bitable supports Scenario G in two roles:

- Source context: Agent creation can read user-configured Bitable records for structured project data.
- Artifact archive: completed docx, ppt, board, and edited document artifacts can be archived back to configured Bitable tables.

It is not a chat persistence layer. Ordinary chat, planning, retrieval traces, process events, and unfinished artifacts are not archived.

## Architecture

The backend uses `backend/app/modules/bitable/openapi_adapter.py` as a thin Feishu OpenAPI adapter. The adapter reuses the existing `FeishuClient` tenant access token flow and calls `/open-apis/bitable/v1/...` endpoints from inside the backend service.

No host-level command line tool is required. Bitable operations run through project code, the same integration style used by document, PPT, canvas, and message capabilities.

Main modules:

- `openapi_adapter.py`: Feishu Bitable OpenAPI transport and error wrapping.
- `service.py`: source filtering, non-blocking query/archive behavior, record normalization, archive upsert semantics.
- `repository.py`: source ownership and archive link persistence.
- `router.py`: authenticated API surface for `/api/v1/bitable/*`.
- `normalizer.py`: converts OpenAPI records and fields into Eko context/archive shapes.

## Configuration

Bitable remains disabled by default:

```env
BITABLE_ENABLED=false
BITABLE_ARCHIVE_ENABLED=false
BITABLE_DEFAULT_WORKSPACE_ID=Feishu_demo_Eko
BITABLE_QUERY_LIMIT=8
```

Feishu credentials are provided through the existing application configuration:

```env
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_BASE_URL=https://open.feishu.cn
```

The configured Feishu app or bot must have access to the target Bitable base and the relevant Bitable OpenAPI permissions.

## Source Configuration

Each source stores:

- `app_token`: the Bitable base/app token, not an access credential.
- `table_id` and optional `view_id`.
- `purpose`: `context`, `archive`, or `both`.
- optional field mappings for title, summary, URL, status, owner, date, and archive fields.

API responses only expose `app_token_masked`. The raw token is not returned to the frontend and should not be printed in logs.

## Behavior

Context query:

- only uses enabled sources owned by the current user.
- only uses `purpose=context` or `purpose=both`.
- returns empty when `BITABLE_ENABLED=false`.
- skips all Bitable reads when `created_by` is missing.
- records failures per source and lets the Agent continue.
- sends retrieved records to source/process channels, not normal chat bubbles.

Archive:

- only uses enabled sources owned by the current user.
- only uses `purpose=archive` or `purpose=both`.
- returns empty when either `BITABLE_ENABLED=false` or `BITABLE_ARCHIVE_ENABLED=false`.
- archives only completed responses with an artifact.
- updates an existing `(session_id, artifact_kind, source_id)` record instead of creating duplicates.
- treats archive failures as non-blocking and records a failed result.

Inspect:

- reads table, fields, and views through Feishu OpenAPI.
- stores a schema snapshot and check status.
- returns an API error to the frontend if the source cannot be inspected.

## Demo Checks

Default-off smoke:

```bash
cd backend && .venv/bin/python -m unittest \
  tests.test_bitable_service \
  tests.test_bitable_router_security \
  tests.test_agent_event_channels \
  tests.test_agent_ppt_design_mode
cd backend && .venv/bin/python -m compileall app
npm run --prefix frontend lint
npm run --prefix frontend build
```

Live Bitable smoke:

1. Set `BITABLE_ENABLED=true`.
2. Configure a source from `/knowledge`.
3. Run inspect and confirm fields/views are displayed.
4. Run query validation and confirm records are returned.
5. Start an Agent request that references the configured table and confirm records appear in source/process UI, not in formal chat text.
6. Set `BITABLE_ARCHIVE_ENABLED=true` and confirm completed docx, ppt, and board artifacts archive or update records without blocking the main task.

## Security Boundary

This phase enforces Eko source ownership isolation. It does not map full Feishu table-level ACLs into Eko. The Feishu app still needs real access to the Bitable base, and Feishu OpenAPI errors are returned as connection or permission failures.
