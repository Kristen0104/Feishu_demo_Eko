import { getApiBaseUrl } from "@/config/eko-env";
import { readAccessToken } from "@/lib/auth-token";

export type CanvasSessionMeta = {
  session_id: string;
  title?: string;
  mode?: string;
  owner_id?: string;
  status?: "idle" | "ai_generating";
  progress?: number;
  canvas_data?: Record<string, unknown>;
  sources?: string[];
};

export async function fetchCanvasSessionMeta(sessionId: string): Promise<CanvasSessionMeta | null> {
  const base = getApiBaseUrl();
  const path = `/api/v1/canvas/sessions/${encodeURIComponent(sessionId)}`;
  const url = base ? `${base}${path}` : path;

  const headers: Record<string, string> = {};
  const token = readAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(url, { headers });
    if (!res.ok) return null;
    const json = (await res.json()) as { code?: number; data?: CanvasSessionMeta };
    if (json.code !== 0 || !json.data) return null;
    return json.data;
  } catch {
    return null;
  }
}
