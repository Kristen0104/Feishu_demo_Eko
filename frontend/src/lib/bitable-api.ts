import { fetchEkoJson } from "@/lib/eko-api";

export type BitablePurpose = "context" | "archive" | "both";

export type BitableSource = {
  id: string;
  workspace_id: string;
  name: string;
  app_token_masked?: string | null;
  table_id: string;
  view_id?: string | null;
  enabled: boolean;
  purpose: BitablePurpose;
  title_field?: string | null;
  summary_field?: string | null;
  url_field?: string | null;
  status_field?: string | null;
  type_field?: string | null;
  owner_field?: string | null;
  date_field?: string | null;
  field_mapping: Record<string, unknown>;
  last_schema_snapshot?: Record<string, unknown>;
  last_check_status?: string | null;
  last_check_error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type BitableSourceInput = {
  workspace_id: string;
  name: string;
  base_id?: string | null;
  app_token?: string | null;
  table_id: string;
  view_id?: string | null;
  purpose: BitablePurpose;
  title_field?: string | null;
  summary_field?: string | null;
  url_field?: string | null;
  status_field?: string | null;
  type_field?: string | null;
  owner_field?: string | null;
  date_field?: string | null;
  field_mapping?: Record<string, unknown>;
};

export type BitableField = {
  field_id?: string;
  field_name?: string;
  name?: string;
  type?: string;
  [key: string]: unknown;
};

export type BitableView = {
  view_id?: string;
  view_name?: string;
  name?: string;
  type?: string;
  [key: string]: unknown;
};

export type BitableInspectResult = {
  source: BitableSource;
  table: Record<string, unknown>;
  fields: BitableField[];
  views: BitableView[];
  raw: Record<string, unknown>;
};

export type BitableRecordContext = {
  source_id: string;
  source_name: string;
  source_type: "bitable";
  table_id: string;
  table_name?: string | null;
  record_id: string;
  title: string;
  summary?: string | null;
  content: string;
  fields: Record<string, unknown>;
  score: number;
  record_url?: string | null;
};

export type BitableQueryResponse = {
  records: BitableRecordContext[];
  failures: Array<{ source_id: string; message: string }>;
  context_text?: string;
  source_snapshot?: {
    sources?: BitableSource[];
    fields?: string[];
  };
};

export type BitableDiscoveryStatus = {
  bound: boolean;
  needs_reauth: boolean;
  identity_label?: string | null;
  mode: "user_oauth" | "tenant_app" | "preset" | "advanced_only";
  message?: string | null;
};

export type BitableBaseOption = {
  id: string;
  name: string;
  source: "user_oauth" | "tenant_app" | "preset";
  app_token_masked?: string | null;
};

export type BitableBaseUrlResolveResponse = {
  base: BitableBaseOption;
  table_id?: string | null;
  view_id?: string | null;
};

export type BitableTableOption = {
  id: string;
  name: string;
};

export type BitableViewOption = {
  id: string;
  name: string;
  type?: string | null;
};

export type BitableFieldOption = {
  id?: string | null;
  name: string;
  type?: string | null;
};

export async function listBitableSources(workspaceId = "Feishu_demo_Eko"): Promise<BitableSource[]> {
  return fetchEkoJson(`/api/v1/bitable/sources?workspace_id=${encodeURIComponent(workspaceId)}`);
}

export async function createBitableSource(payload: BitableSourceInput): Promise<BitableSource> {
  return fetchEkoJson("/api/v1/bitable/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateBitableSource(sourceId: string, payload: Partial<BitableSourceInput> & { enabled?: boolean }): Promise<BitableSource> {
  return fetchEkoJson(`/api/v1/bitable/sources/${encodeURIComponent(sourceId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteBitableSource(sourceId: string): Promise<void> {
  await fetchEkoJson<null>(`/api/v1/bitable/sources/${encodeURIComponent(sourceId)}`, {
    method: "DELETE",
  });
}

export async function inspectBitableSource(sourceId: string): Promise<BitableInspectResult> {
  return fetchEkoJson(`/api/v1/bitable/sources/${encodeURIComponent(sourceId)}/inspect`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function queryBitableRecords(query: string, limit = 5, workspaceId = "Feishu_demo_Eko"): Promise<BitableQueryResponse> {
  return fetchEkoJson("/api/v1/bitable/query", {
    method: "POST",
    body: JSON.stringify({ workspace_id: workspaceId, query, limit }),
  });
}

export async function getBitableDiscoveryStatus(): Promise<BitableDiscoveryStatus> {
  return fetchEkoJson("/api/v1/bitable/discovery/status", { cache: "no-store" });
}

export async function listBitableBases(): Promise<BitableBaseOption[]> {
  return fetchEkoJson("/api/v1/bitable/discovery/bases", { cache: "no-store" });
}

export async function resolveBitableBaseUrl(url: string): Promise<BitableBaseUrlResolveResponse> {
  return fetchEkoJson("/api/v1/bitable/discovery/resolve-url", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function listBitableTables(baseId: string): Promise<BitableTableOption[]> {
  return fetchEkoJson(`/api/v1/bitable/discovery/tables?base_id=${encodeURIComponent(baseId)}`, { cache: "no-store" });
}

export async function listBitableViews(baseId: string, tableId: string): Promise<BitableViewOption[]> {
  return fetchEkoJson(
    `/api/v1/bitable/discovery/views?base_id=${encodeURIComponent(baseId)}&table_id=${encodeURIComponent(tableId)}`,
    { cache: "no-store" },
  );
}

export async function listBitableFields(baseId: string, tableId: string): Promise<BitableFieldOption[]> {
  return fetchEkoJson(
    `/api/v1/bitable/discovery/fields?base_id=${encodeURIComponent(baseId)}&table_id=${encodeURIComponent(tableId)}`,
    { cache: "no-store" },
  );
}
