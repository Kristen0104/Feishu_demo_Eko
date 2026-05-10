import { getApiBaseUrl } from "@/config/eko-env";
import { readAccessToken } from "@/lib/auth-token";

export type SyncSession = {
  session_id: string;
  source: string;
  title: string;
  summary: string;
  status: string;
  opened_at: string;
  updated_at: string;
  chat_id?: string | null;
  message_id?: string | null;
  context_size?: number;
  instruction?: string | null;
  intent?: string | null;
  artifact?: {
    kind?: string | null;
    intent?: string | null;
    job_id?: string | null;
    status?: string | null;
    progress?: number | null;
    current_step?: string | null;
    download_url?: string | null;
    error_message?: string | null;
    bitable_archive_results?: Array<{
      source_id?: string | null;
      record_id?: string | null;
      record_url?: string | null;
      status?: string | null;
      message?: string | null;
      error?: string | null;
    }>;
    [key: string]: unknown;
  } | null;
  messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
    sender_open_id?: string | null;
    sender_union_id?: string | null;
    sender_name?: string | null;
    platform_user_id?: string | null;
    platform_display_name?: string | null;
    avatar_url?: string | null;
  }>;
  context_messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
    sender_open_id?: string | null;
    sender_union_id?: string | null;
    sender_name?: string | null;
    platform_user_id?: string | null;
    platform_display_name?: string | null;
    avatar_url?: string | null;
  }>;
  selected_context_messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
    sender_open_id?: string | null;
    sender_union_id?: string | null;
    sender_name?: string | null;
    platform_user_id?: string | null;
    platform_display_name?: string | null;
    avatar_url?: string | null;
  }>;
};

export type FetchSyncSessionResult =
  | { ok: true; session: SyncSession }
  | {
      ok: false;
      reason: "not_found" | "unauthorized" | "forbidden" | "network" | "server" | "invalid";
      status?: number;
      message?: string;
    };

function resultFromStatus(status: number, message?: string): FetchSyncSessionResult {
  if (status === 404) return { ok: false, reason: "not_found", status, message };
  if (status === 401) return { ok: false, reason: "unauthorized", status, message };
  if (status === 403) return { ok: false, reason: "forbidden", status, message };
  if (status >= 500) return { ok: false, reason: "server", status, message };
  return { ok: false, reason: "invalid", status, message };
}

function readResponseMessage(body: unknown): string | undefined {
  if (!body || typeof body !== "object") return undefined;
  const payload = body as { message?: unknown; detail?: unknown };
  if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
  if (typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;
  return undefined;
}

export async function fetchSyncSessionResult(sessionId: string): Promise<FetchSyncSessionResult> {
  const base = getApiBaseUrl();
  const path = `/api/v1/sync/sessions/${encodeURIComponent(sessionId)}`;
  const url = base ? `${base}${path}` : path;

  const headers: Record<string, string> = {};
  const token = readAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(url, { headers, cache: "no-store" });
    const json = (await res.json().catch(() => null)) as { code?: number; data?: SyncSession | null; message?: string } | null;
    if (!res.ok) return resultFromStatus(res.status, readResponseMessage(json));
    if (!json || json.code !== 0 || !json.data) {
      return {
        ok: false,
        reason: "invalid",
        status: res.status,
        message: readResponseMessage(json) ?? "会话数据格式无效",
      };
    }
    return { ok: true, session: json.data };
  } catch {
    return { ok: false, reason: "network", message: "网络暂时不可用" };
  }
}

export async function fetchSyncSession(sessionId: string): Promise<SyncSession | null> {
  const result = await fetchSyncSessionResult(sessionId);
  return result.ok ? result.session : null;
}
