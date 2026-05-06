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
 * Protocol mock is a demo fallback, not a production substitute for backend realtime.
 * Production builds only enable it when explicitly requested.
 */
export function isProtocolMockFallbackEnabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_EKO_PROTOCOL_MOCK;
  if (raw === "true") return true;
  if (raw === "false") return false;
  return process.env.NODE_ENV !== "production";
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

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  return `${protocol}://${host}/api/v1/sync/ws/session/${encId}${q}`;
}
