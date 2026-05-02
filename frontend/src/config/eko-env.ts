/**
 * Public env for Eko API / WebSocket. Same-origin relative paths work when unset.
 */

export function getApiBaseUrl(): string {
  const raw = typeof process !== "undefined" ? process.env.NEXT_PUBLIC_EKO_API_BASE ?? "" : "";
  return raw.replace(/\/$/, "");
}

/** When false, realtime hook skips opening a WebSocket (protocol mock / SSE only). */
export function isWebSocketEnabled(): boolean {
  return process.env.NEXT_PUBLIC_EKO_USE_WS !== "false";
}

/**
 * Build ws/wss URL for session channel. Prefer NEXT_PUBLIC_EKO_WS_BASE (e.g. ws://127.0.0.1:8000).
 * Falls back to deriving from window location when api base is empty (same host).
 */
export function buildSessionWebSocketUrl(sessionId: string, token: string | null): string | null {
  if (typeof window === "undefined") return null;

  const explicit = process.env.NEXT_PUBLIC_EKO_WS_BASE?.replace(/\/$/, "");
  const encId = encodeURIComponent(sessionId);
  const q = token ? `?token=${encodeURIComponent(token)}` : "";

  if (explicit) {
    return `${explicit}/ws/session/${encId}${q}`;
  }

  const api = getApiBaseUrl();
  if (api) {
    try {
      const base = api.startsWith("http") ? api : `http://${api}`;
      const u = new URL(base);
      u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
      u.pathname = `/ws/session/${encId}`;
      u.search = token ? `token=${encodeURIComponent(token)}` : "";
      u.hash = "";
      return u.toString();
    } catch {
      /* fall through */
    }
  }

  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/session/${encId}${q}`;
}
