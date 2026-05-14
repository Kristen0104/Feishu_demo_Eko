/**
 * Public env for Eko API / WebSocket. Same-origin relative paths work when unset.
 */

export function getApiBaseUrl(): string {
  const raw = typeof process !== "undefined" ? process.env.NEXT_PUBLIC_EKO_API_BASE ?? "" : "";
  return raw.replace(/\/$/, "");
}

/** When false, realtime hook skips opening a WebSocket. */
export function isWebSocketEnabled(): boolean {
  return process.env.NEXT_PUBLIC_EKO_USE_WS !== "false";
}

/**
 * Build ws/wss URL for session channel. Prefer NEXT_PUBLIC_EKO_WS_BASE (e.g. ws://127.0.0.1:8000).
 * Falls back to local backend in development, or same host in production.
 */
export function buildSessionWebSocketUrl(sessionId: string, token: string | null): string | null {
  if (typeof window === "undefined") return null;

  const explicit = process.env.NEXT_PUBLIC_EKO_WS_BASE?.replace(/\/$/, "");
  const encId = encodeURIComponent(sessionId);
  const q = token ? `?token=${encodeURIComponent(token)}` : "";

  if (explicit) {
    return `${explicit}/api/v1/sync/ws/session/${encId}${q}`;
  }

  const api = getApiBaseUrl();
  if (api) {
    try {
      const base = api.startsWith("http") ? api : `http://${api}`;
      const u = new URL(base);
      u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
      u.pathname = `/api/v1/sync/ws/session/${encId}`;
      u.search = token ? `token=${encodeURIComponent(token)}` : "";
      u.hash = "";
      return u.toString();
    } catch {
      /* fall through */
    }
  }

  const fallbackBase =
    process.env.NODE_ENV === "development"
      ? "ws://127.0.0.1:8000"
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
  return `${fallbackBase}/api/v1/sync/ws/session/${encId}${q}`;
}
