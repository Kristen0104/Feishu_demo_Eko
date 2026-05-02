"use client";

import { useEffect, useRef } from "react";

import { buildSessionWebSocketUrl, isWebSocketEnabled } from "@/config/eko-env";
import { readAccessToken } from "@/lib/auth-token";
import { runProtocolMockSequence } from "@/lib/realtime/protocol-mock";
import { useAgentRuntimeStore } from "@/store/agent-runtime-store";

export type UseEkoSessionRealtimeOptions = {
  sessionId: string;
  /** When false, never runs protocol mock (only useful if backend WS always works). Default true. */
  enableProtocolMock?: boolean;
  /** Skip WebSocket and run mock only (e.g. Storybook). */
  forceMock?: boolean;
};

/**
 * Subscribes session to agent-runtime store, opens WebSocket when enabled, otherwise runs
 * a protocol-compatible mock sequence once so Mission Control / doc stream stay demonstrable.
 */
export function useEkoSessionRealtime({
  sessionId,
  enableProtocolMock = true,
  forceMock = false,
}: UseEkoSessionRealtimeOptions): void {
  const ensureSession = useAgentRuntimeStore((s) => s.ensureSession);
  const patchSession = useAgentRuntimeStore((s) => s.patchSession);
  const ingest = useAgentRuntimeStore((s) => s.ingestEnvelope);

  useEffect(() => {
    ensureSession(sessionId);
  }, [sessionId, ensureSession]);

  useEffect(() => {
    const mockStartedRef = { current: false };

    const startMockOnce = () => {
      if (!enableProtocolMock || mockStartedRef.current) return undefined;
      mockStartedRef.current = true;
      patchSession(sessionId, { useMockFallback: true });
      return runProtocolMockSequence(sessionId, ingest);
    };

    if (forceMock) {
      patchSession(sessionId, { wsStatus: "closed", useMockFallback: true });
      const cancel = startMockOnce();
      return () => cancel?.();
    }

    if (!isWebSocketEnabled()) {
      patchSession(sessionId, { wsStatus: "closed", useMockFallback: true });
      const cancel = startMockOnce();
      return () => cancel?.();
    }

    const url = buildSessionWebSocketUrl(sessionId, readAccessToken());
    if (!url) {
      patchSession(sessionId, { wsStatus: "error", useMockFallback: true });
      const cancel = startMockOnce();
      return () => cancel?.();
    }

    patchSession(sessionId, { wsStatus: "connecting", useMockFallback: false });

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      patchSession(sessionId, { wsStatus: "error", useMockFallback: true });
      const cancel = startMockOnce();
      return () => cancel?.();
    }

    let cancelled = false;
    let mockCancel: (() => void) | undefined;

    ws.onopen = () => {
      if (cancelled) return;
      patchSession(sessionId, { wsStatus: "open", useMockFallback: false });
    };

    ws.onmessage = (ev) => {
      if (cancelled) return;
      try {
        const raw = JSON.parse(String(ev.data)) as unknown;
        ingest(sessionId, raw);
      } catch {
        /* ignore non-json frames */
      }
    };

    const onWsUnavailable = () => {
      if (cancelled) return;
      patchSession(sessionId, { wsStatus: "error", useMockFallback: true });
      if (!mockCancel) mockCancel = startMockOnce();
    };

    ws.onerror = onWsUnavailable;

    ws.onclose = () => {
      if (cancelled) return;
      patchSession(sessionId, { wsStatus: "closed" });
      // If connection never opened, trigger mock once (many browsers don't fire error reliably).
      if (ws.readyState !== WebSocket.OPEN && enableProtocolMock && !mockStartedRef.current) {
        mockCancel = startMockOnce();
      }
    };

    return () => {
      cancelled = true;
      mockCancel?.();
      if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId, enableProtocolMock, forceMock, ensureSession, patchSession, ingest]);
}
