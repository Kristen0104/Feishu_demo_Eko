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
  onTickRef.current = onTick;

  useEffect(() => {
    if (!enabled) return;
    const timer = window.setInterval(() => onTickRef.current(), intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs]);
}

