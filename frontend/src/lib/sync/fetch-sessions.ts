import { getApiBaseUrl } from "@/config/eko-env";
import { readAccessToken } from "@/lib/auth-token";

export type SyncSession = {
  session_id: string;
  source: string;
  title: string;
  summary: string;
  status: string;
  user_id?: string | null;
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
    [key: string]: unknown;
  } | null;
  messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
  }>;
  context_messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
  }>;
  selected_context_messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
  }>;
};

export async function fetchSyncSessions(): Promise<SyncSession[]> {
  const base = getApiBaseUrl();
  if (!base) return [];

  const path = "/api/v1/sync/sessions";
  const url = `${base}${path}`;
  const headers: Record<string, string> = {};
  const token = readAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 1800);
  try {
    const res = await fetch(url, { headers, cache: "no-store", signal: controller.signal });
    if (!res.ok) return [];
    const json = (await res.json()) as { code?: number; data?: SyncSession[] };
    if (json.code !== 0 || !Array.isArray(json.data)) return [];
    return json.data;
  } catch {
    return [];
  } finally {
    window.clearTimeout(timeout);
  }
}
