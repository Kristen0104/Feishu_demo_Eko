"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { runProtocolMockSequence } from "@/lib/realtime/protocol-mock";
import { useAgentRuntimeStore } from "@/store/agent-runtime-store";

export function DemoControlPanel({ sessionId }: { sessionId: string }) {
  const [open, setOpen] = useState(false);
  const cancelRef = useRef<(() => void) | null>(null);
  const ingest = useAgentRuntimeStore((s) => s.ingestEnvelope);
  const reset = useAgentRuntimeStore((s) => s.resetSession);
  const slice = useAgentRuntimeStore((s) => s.sessions[sessionId]);

  const isDemo = useMemo(() => sessionId.startsWith("demo-"), [sessionId]);

  useEffect(() => {
    function onKeyDown(ev: KeyboardEvent) {
      if ((ev.ctrlKey || ev.metaKey) && ev.shiftKey && ev.key.toLowerCase() === "d") {
        ev.preventDefault();
        setOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const stop = useCallback(() => {
    cancelRef.current?.();
    cancelRef.current = null;
  }, []);

  const runFlow = useCallback(() => {
    stop();
    reset(sessionId);
    cancelRef.current = runProtocolMockSequence(sessionId, ingest);
  }, [ingest, reset, sessionId, stop]);

  const complete = useCallback(() => {
    ingest(sessionId, { event: "result.created", status: "completed", message: "任务完成。", payload: { response: { status: "completed" }, session_id: sessionId } });
  }, [ingest, sessionId]);

  if (!isDemo) return null;

  return open ? (
    <div className="fixed bottom-4 right-4 z-[9999] w-[340px] rounded-[16px] border border-slate-200 bg-white p-3 shadow-[0_18px_44px_rgba(15,23,42,0.18)]">
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-semibold text-slate-900">Demo 控制面板</p>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-lg px-2 py-1 text-[12px] font-semibold text-slate-500 hover:bg-slate-50"
        >
          关闭
        </button>
      </div>
      <p className="mt-1 text-[11px] text-slate-500">
        快捷键：<span className="rounded bg-slate-100 px-1 font-mono">Ctrl/⌘ + Shift + D</span>
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={runFlow}
          className="inline-flex h-8 items-center rounded-[10px] bg-blue-600 px-3 text-[12px] font-semibold text-white hover:bg-blue-700"
        >
          一键跑状态流
        </button>
        <button
          type="button"
          onClick={stop}
          className="inline-flex h-8 items-center rounded-[10px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 hover:bg-slate-50"
        >
          停止
        </button>
        <button
          type="button"
          onClick={() => reset(sessionId)}
          className="inline-flex h-8 items-center rounded-[10px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 hover:bg-slate-50"
        >
          重置
        </button>
        <button
          type="button"
          onClick={complete}
          className="inline-flex h-8 items-center rounded-[10px] bg-emerald-600 px-3 text-[12px] font-semibold text-white hover:bg-emerald-700"
        >
          直接完成
        </button>
      </div>

      <div className="mt-3 rounded-[12px] border border-slate-100 bg-slate-50 px-3 py-2 text-[11px] text-slate-600">
        <div className="flex items-center justify-between">
          <span>phase</span>
          <span className="font-mono text-slate-800">{slice?.phase ?? "—"}</span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <span>ws</span>
          <span className="font-mono text-slate-800">{slice?.wsStatus ?? "—"}</span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <span>progress</span>
          <span className="font-mono text-slate-800">{Math.round((slice?.progress ?? 0) * 100)}%</span>
        </div>
      </div>
    </div>
  ) : null;
}

