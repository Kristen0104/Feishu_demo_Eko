import { readAccessToken } from "@/lib/auth-token";
import { apiUrl } from "@/lib/eko-api";

function bearerHeaders(): HeadersInit {
  const token = readAccessToken();
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export type StreamCallbacks = {
  onChunk?: (text: string) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
};

/**
 * Backend contract from document/router.py — SSE lines:
 * data: {"session_id","status":"generating"}
 * data: {"content": chunk}
 * data: {"status":"completed"|"failed",...}
 */
export async function streamDocumentGeneration(
  body: Record<string, unknown>,
  callbacks: StreamCallbacks,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(apiUrl("/api/v1/document/generate/stream"), {
      method: "POST",
      headers: bearerHeaders(),
      body: JSON.stringify(body),
    });
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e.message : "network error");
    return;
  }

  if (!res.ok || !res.body) {
    callbacks.onError?.(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;
        let data: unknown;
        try {
          data = JSON.parse(jsonStr) as unknown;
        } catch {
          continue;
        }
        if (!data || typeof data !== "object") continue;
        const o = data as Record<string, unknown>;
        if (typeof o.content === "string" && o.content.length) {
          callbacks.onChunk?.(o.content);
        }
        if (o.status === "completed") {
          callbacks.onDone?.();
        }
        if (o.status === "failed") {
          callbacks.onError?.(typeof o.error === "string" ? o.error : "stream failed");
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/** Optional unified agent execute SSE — present when backend adds route. */
export async function streamAgentExecute(
  body: { session_id: string; query: string; stream?: boolean },
  callbacks: StreamCallbacks,
): Promise<boolean> {
  let res: Response;
  try {
    res = await fetch(apiUrl("/api/v1/agent/execute"), {
      method: "POST",
      headers: bearerHeaders(),
      body: JSON.stringify({ ...body, stream: body.stream ?? true }),
    });
  } catch {
    return false;
  }

  if (res.status === 404 || res.status === 405 || res.status === 501) {
    return false;
  }

  if (!res.ok || !res.body) {
    callbacks.onError?.(`HTTP ${res.status}`);
    return true;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;
        let data: unknown;
        try {
          data = JSON.parse(jsonStr) as unknown;
        } catch {
          continue;
        }
        if (!data || typeof data !== "object") continue;
        const o = data as Record<string, unknown>;
        const type = typeof o.type === "string" ? o.type : "";

        if (type === "DOC_STREAM") {
          const payload = (o.payload ?? {}) as Record<string, unknown>;
          const chunk =
            typeof payload.chunk === "string"
              ? payload.chunk
              : typeof payload.text === "string"
                ? payload.text
                : "";
          if (chunk) callbacks.onChunk?.(chunk);
          continue;
        }

        if (typeof o.chunk === "string") {
          callbacks.onChunk?.(o.chunk);
        }
        if (typeof o.markdown === "string") {
          callbacks.onChunk?.(o.markdown);
        }
      }
    }
    callbacks.onDone?.();
  } finally {
    reader.releaseLock();
  }

  return true;
}
