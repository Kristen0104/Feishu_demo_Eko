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
};

export async function fetchSyncSession(sessionId: string): Promise<SyncSession | null> {
  const base = getApiBaseUrl();
  const path = `/api/v1/sync/sessions/${encodeURIComponent(sessionId)}`;
  const url = base ? `${base}${path}` : path;

  const headers: Record<string, string> = {};
  const token = readAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(url, { headers, cache: "no-store" });
    if (!res.ok) return null;
    const json = (await res.json()) as { code?: number; data?: SyncSession | null };
    if (json.code !== 0 || !json.data) return null;
    return json.data;
  } catch {
    return null;
  }
}
