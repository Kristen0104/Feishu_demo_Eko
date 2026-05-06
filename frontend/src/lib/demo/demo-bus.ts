"use client";

export type DemoBusEvent =
  | { type: "CARD_STATUS"; sessionId: string; statusText: string; progress?: number }
  | { type: "PPT_EXPORTED"; sessionId: string; filename: string }
  | { type: "ARCHIVED"; sessionId: string; docTitle: string };

const CHANNEL = "eko-demo-bus";
const STORAGE_KEY = "eko-demo-bus:last";

function safeJsonParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function publishDemoEvent(ev: DemoBusEvent) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ev, at: Date.now() }));
  } catch {
    /* ignore */
  }
  try {
    const ch = new BroadcastChannel(CHANNEL);
    ch.postMessage(ev);
    ch.close();
  } catch {
    /* ignore */
  }
}

export function subscribeDemoEvents(handler: (ev: DemoBusEvent) => void): () => void {
  const onStorage = (e: StorageEvent) => {
    if (e.key !== STORAGE_KEY) return;
    const parsed = safeJsonParse<{ ev: DemoBusEvent }>(e.newValue);
    if (parsed?.ev) handler(parsed.ev);
  };
  window.addEventListener("storage", onStorage);

  let ch: BroadcastChannel | null = null;
  try {
    ch = new BroadcastChannel(CHANNEL);
    ch.onmessage = (e) => handler(e.data as DemoBusEvent);
  } catch {
    /* ignore */
  }

  // deliver last event once (useful for late-opened tabs)
  const last = safeJsonParse<{ ev: DemoBusEvent }>(localStorage.getItem(STORAGE_KEY));
  if (last?.ev) queueMicrotask(() => handler(last.ev));

  return () => {
    window.removeEventListener("storage", onStorage);
    if (ch) ch.close();
  };
}

