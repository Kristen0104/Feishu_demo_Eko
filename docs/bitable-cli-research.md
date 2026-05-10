# Bitable Official CLI Research

Last checked: 2026-05-10

## Sources

- Official CLI repository: https://github.com/larksuite/cli
- Official Base skill: https://github.com/larksuite/cli/blob/main/skills/lark-base/SKILL.md
- Relevant references under `skills/lark-base/references/`
- Local help checked with `npx -y @larksuite/cli base +record-search --help`

## Findings

The official CLI binary is `lark-cli`. It is published as the npm package `@larksuite/cli` and can be installed with:

```bash
npm install -g @larksuite/cli
npx skills add larksuite/cli -y -g
```

The Base skill requires Base operations to use shortcut commands in the form:

```bash
lark-cli base +...
```

The README documents structured output modes:

```bash
--format json
--format pretty
--format table
--format ndjson
--format csv
```

Local help for `@larksuite/cli` v1.0.27 shows that Base shortcuts are not completely uniform: `+record-search`, `+record-list`, and `+record-get` expose `--format json`, while commands such as `+table-list`, `+table-get`, `+field-list`, `+view-list`, and `+record-upsert` expose `--jq` but reject `--format`.

For this integration, the backend adapter uses the common Base shortcut option `--jq .` and parses JSON only. If a command does not return valid JSON, the adapter treats it as a CLI error instead of attempting a loose text parser.

## Authentication

The CLI authentication path is:

```bash
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status
```

Base commands should explicitly use an identity flag. The Base skill recommends user identity for personal/team Base resources:

```bash
--as user
```

The backend exposes configuration through environment variables:

- `LARK_CLI_BINARY`, default `lark-cli`
- `LARK_CLI_TIMEOUT_SECONDS`, default `20`
- `LARK_CLI_CONFIG_DIR`, optional CLI config directory
- `BITABLE_ENABLED`, default `false`
- `BITABLE_DEFAULT_WORKSPACE_ID`, default `Feishu_demo_Eko`
- `BITABLE_QUERY_LIMIT`, default `8`
- `BITABLE_ARCHIVE_ENABLED`, default `false`

If `LARK_CLI_CONFIG_DIR` is set, the adapter exports it as `LARK_CLI_CONFIG_DIR` and `LARK_CONFIG_DIR` for the child process.

## Relevant Commands

All commands below support `--as user` and `--format json` where relevant.

### Tables

```bash
lark-cli base +table-list --base-token app_xxx --offset 0 --limit 50 --jq . --as user
lark-cli base +table-get --base-token app_xxx --table-id tbl_xxx --jq . --as user
```

`+table-get` returns table metadata plus field and view information, which is useful for source inspection.

### Fields

```bash
lark-cli base +field-list --base-token app_xxx --table-id tbl_xxx --offset 0 --limit 100 --jq . --as user
```

### Views

```bash
lark-cli base +view-list --base-token app_xxx --table-id tbl_xxx --offset 0 --limit 100 --jq . --as user
```

### Records

```bash
lark-cli base +record-search \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --json '{"keyword":"项目","search_fields":["标题"],"select_fields":["标题","状态"],"limit":8}' \
  --jq . \
  --as user

lark-cli base +record-list \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --view-id viw_xxx \
  --limit 50 \
  --jq . \
  --as user

lark-cli base +record-get \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --record-id rec_xxx \
  --jq . \
  --as user
```

The record read SOP states that `+record-search` is for text keyword search only. Structured filters, sorting, and Top N style reads should use views or `+data-query`.

### Writes

```bash
lark-cli base +record-upsert \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --json '{"标题":"Eko 文档","状态":"completed"}' \
  --jq . \
  --as user

lark-cli base +record-upsert \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --record-id rec_xxx \
  --json '{"状态":"completed"}' \
  --jq . \
  --as user
```

Despite the `upsert` command name, the official reference clarifies that it creates when `--record-id` is absent and updates when `--record-id` is present. It does not perform automatic business-key matching.

For creating record links:

```bash
lark-cli base +record-share-link-create \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --record-ids rec_xxx \
  --jq . \
  --as user
```

### Data Query

```bash
lark-cli base +data-query \
  --base-token app_xxx \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"tbl_xxx"}},"measures":[{"field_name":"城市","aggregation":"count","alias":"count"}],"shaper":{"format":"flat"}}' \
  --as user
```

`+data-query` is for aggregation. It is not a replacement for raw record retrieval.

## Error Handling

The CLI exits non-zero for missing auth, invalid arguments, permission problems, and API errors. The adapter captures stdout/stderr, redacts token-like values, and raises `BitableCliError` with:

- command without sensitive values
- exit code
- sanitized stderr/stdout excerpt

Timeouts are converted to `BitableCliError`. Bitable failures are non-blocking in Agent retrieval and archive flows.

## Adapter Decision

Use official CLI shortcuts first:

- `+table-list`
- `+table-get`
- `+field-list`
- `+view-list`
- `+record-search`
- `+record-list`
- `+record-upsert`
- `+record-share-link-create`
- `+data-query`

Do not implement a Bitable REST SDK. The Eko backend only does source configuration, command invocation, JSON parsing, normalization, retrieval merging, Agent tool registration, UI display, and archive link tracking.
