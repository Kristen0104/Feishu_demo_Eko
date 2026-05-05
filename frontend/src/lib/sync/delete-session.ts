import { getApiBaseUrl } from "@/config/eko-env";
import { readAccessToken } from "@/lib/auth-token";

export async function deleteSyncSession(sessionId: string): Promise<boolean> {
  const base = getApiBaseUrl();
  const path = `/api/v1/sync/sessions/${encodeURIComponent(sessionId)}`;
  const url = base ? `${base}${path}` : path;

  const headers: Record<string, string> = {};
  const token = readAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(url, { method: "DELETE", headers });
    if (!res.ok) return false;
    const json = (await res.json().catch(() => null)) as { code?: number; data?: { deleted?: boolean } | null } | null;
    if (!json) return true;
    if (json.code !== 0) return false;
    return true;
  } catch {
    return false;
  }
}
