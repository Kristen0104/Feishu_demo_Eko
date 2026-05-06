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

export type AgentChatStreamEvent = {
  event:
    | "turn.started"
    | "intent.recognized"
    | "context.loaded"
    | "retrieval.started"
    | "retrieval.completed"
    | "plan.created"
    | "plan.summary"
    | "plan.step"
    | "tool.selected"
    | "tool.started"
    | "tool.completed"
    | "clarification.requested"
    | "result.created"
    | "turn.failed";
  status?: "pending" | "running" | "completed" | "blocked" | "failed";
  message?: string;
  payload?: Record<string, unknown>;
};

export async function streamAgentChat(
  body: Record<string, unknown>,
  onEvent: (event: AgentChatStreamEvent) => void,
): Promise<boolean> {
  let res: Response;
  try {
    res = await fetch(apiUrl("/api/v1/agent/chat/stream"), {
      method: "POST",
      headers: bearerHeaders(),
      body: JSON.stringify(body),
    });
  } catch {
    return false;
  }

  if (res.status === 404 || res.status === 405 || res.status === 501) {
    return false;
  }

  if (!res.ok || !res.body) {
    onEvent({ event: "turn.failed", status: "failed", message: `HTTP ${res.status}`, payload: { error: `HTTP ${res.status}` } });
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
        try {
          const event = JSON.parse(jsonStr) as AgentChatStreamEvent;
          if (event && typeof event === "object" && typeof event.event === "string") {
            onEvent(event);
          }
        } catch {
          /* ignore malformed stream chunks */
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return true;
}
