"use client";

import { useEffect } from "react";

import { buildSessionWebSocketUrl, isWebSocketEnabled } from "@/config/eko-env";
import { readAccessToken } from "@/lib/auth-token";
import { useAgentRuntimeStore } from "@/store/agent-runtime-store";

export type UseEkoSessionRealtimeOptions = {
  sessionId: string;
  onEnvelope?: (raw: unknown) => void;
};

/**
 * Subscribes session to agent-runtime store and opens WebSocket when enabled.
 */
export function useEkoSessionRealtime({
  sessionId,
  onEnvelope,
}: UseEkoSessionRealtimeOptions): void {
  const ensureSession = useAgentRuntimeStore((s) => s.ensureSession);
  const patchSession = useAgentRuntimeStore((s) => s.patchSession);
  const ingest = useAgentRuntimeStore((s) => s.ingestEnvelope);

  useEffect(() => {
    ensureSession(sessionId);
  }, [sessionId, ensureSession]);

  useEffect(() => {
    if (!isWebSocketEnabled()) {
      patchSession(sessionId, { wsStatus: "closed" });
      return;
    }

    const url = buildSessionWebSocketUrl(sessionId, readAccessToken());
    if (!url) {
      patchSession(sessionId, { wsStatus: "error" });
      return;
    }

    patchSession(sessionId, { wsStatus: "connecting" });

    let opened = false;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      patchSession(sessionId, { wsStatus: "error" });
      return;
    }

    let cancelled = false;

    ws.onopen = () => {
      if (cancelled) return;
      opened = true;
      patchSession(sessionId, { wsStatus: "open" });
    };

    ws.onmessage = (ev) => {
      if (cancelled) return;
      try {
        const raw = JSON.parse(String(ev.data)) as unknown;
        ingest(sessionId, raw);
        onEnvelope?.(raw);
      } catch {
        /* ignore non-json frames */
      }
    };

    const onWsUnavailable = () => {
      if (cancelled) return;
      patchSession(sessionId, { wsStatus: "error" });
    };

    ws.onerror = onWsUnavailable;

    ws.onclose = () => {
      if (cancelled) return;
      patchSession(sessionId, { wsStatus: "closed" });
      if (!opened) {
        patchSession(sessionId, { wsStatus: "error" });
      }
    };

    return () => {
      cancelled = true;
      if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId, ensureSession, patchSession, ingest, onEnvelope]);
}
