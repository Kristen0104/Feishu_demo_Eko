"use client";

import { useEffect } from "react";

import { buildSessionWebSocketUrl, isProtocolMockFallbackEnabled, isWebSocketEnabled } from "@/config/eko-env";
import { readAccessToken } from "@/lib/auth-token";
import { runProtocolMockSequence } from "@/lib/realtime/protocol-mock";
import { useAgentRuntimeStore } from "@/store/agent-runtime-store";

export type UseEkoSessionRealtimeOptions = {
  sessionId: string;
  /** When false, never runs protocol mock. Defaults to dev-only unless NEXT_PUBLIC_EKO_PROTOCOL_MOCK=true. */
  enableProtocolMock?: boolean;
  /** Skip WebSocket and run mock only (e.g. Storybook). */
  forceMock?: boolean;
  onEnvelope?: (raw: unknown) => void;
};

/**
 * Subscribes session to agent-runtime store and opens WebSocket when enabled.
 * Demo protocol mock only runs when explicitly enabled by options/env.
 */
export function useEkoSessionRealtime({
  sessionId,
  enableProtocolMock = isProtocolMockFallbackEnabled(),
  forceMock = false,
  onEnvelope,
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
      patchSession(sessionId, { wsStatus: "closed", useMockFallback: enableProtocolMock });
      const cancel = startMockOnce();
      return () => cancel?.();
    }

    const url = buildSessionWebSocketUrl(sessionId, readAccessToken());
    if (!url) {
      patchSession(sessionId, { wsStatus: "error", useMockFallback: enableProtocolMock });
      const cancel = startMockOnce();
      return () => cancel?.();
    }

    patchSession(sessionId, { wsStatus: "connecting", useMockFallback: false });

    let opened = false;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      patchSession(sessionId, { wsStatus: "error", useMockFallback: enableProtocolMock });
      const cancel = startMockOnce();
      return () => cancel?.();
    }

    let cancelled = false;
    let mockCancel: (() => void) | undefined;

    ws.onopen = () => {
      if (cancelled) return;
      opened = true;
      patchSession(sessionId, { wsStatus: "open", useMockFallback: false });
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
      patchSession(sessionId, { wsStatus: "error", useMockFallback: enableProtocolMock });
      if (!mockCancel) mockCancel = startMockOnce();
    };

    ws.onerror = onWsUnavailable;

    ws.onclose = () => {
      if (cancelled) return;
      patchSession(sessionId, { wsStatus: "closed" });
      // If connection never opened, trigger mock once (many browsers don't fire error reliably).
      if (!opened && enableProtocolMock && !mockStartedRef.current) {
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
  }, [sessionId, enableProtocolMock, forceMock, ensureSession, patchSession, ingest, onEnvelope]);
}
