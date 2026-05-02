"use client";

import { useEffect, useRef } from "react";

export function useMockWebSocket({
  enabled = true,
  intervalMs = 10000,
  onTick,
}: {
  enabled?: boolean;
  intervalMs?: number;
  onTick: () => void;
}) {
  const onTickRef = useRef(onTick);

  useEffect(() => {
    onTickRef.current = onTick;
  }, [onTick]);

  useEffect(() => {
    if (!enabled) return;
    const timer = window.setInterval(() => {
      try {
        onTickRef.current();
      } catch {
        /* 防止 setState 等在定时器里抛错变成 Uncaught (in promise) undefined */
      }
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs]);
}

