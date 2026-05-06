"use client";

import type { Editor } from "@tldraw/editor";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";

import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { runGrowthDemo } from "@/lib/tldraw/growth-storyboard";
import { storyCardsFromSessionQuery } from "@/lib/tldraw/story-cards-from-session";

function persistenceKeyFor(sessionId: string) {
  return `eko-tldraw-embed-v1-${sessionId}`;
}

export function EmbeddedEkoCanvas({ sessionId, readOnly = false }: { sessionId: string; readOnly?: boolean }) {
  const persistenceKey = useMemo(() => persistenceKeyFor(sessionId), [sessionId]);
  const prefersReducedMotion = usePrefersReducedMotion();
  const storyCards = useMemo(() => storyCardsFromSessionQuery(sessionId), [sessionId]);

  const editorRef = useRef<Editor | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2600);
  }, []);

  const streamOpts = useMemo(
    () =>
      prefersReducedMotion
        ? { reducedMotion: true as const, mockWsMessageGapMs: 0, shapeRevealDurationMs: 1 }
        : { reducedMotion: false as const, mockWsMessageGapMs: 240, shapeRevealDurationMs: 420 },
    [prefersReducedMotion],
  );

  const onMount = useCallback((editor: Editor) => {
    editorRef.current = editor;
    editor.user.updateUserPreferences({ colorScheme: "light" });
    queueMicrotask(() => editor.zoomToFit({ animation: { duration: 0 } }));
    return () => {
      editorRef.current = null;
    };
  }, []);

  const clearCanvas = useCallback(() => {
    const editor = editorRef.current;
    if (!editor || busy) return;
    editor.selectAll();
    const ids = editor.getSelectedShapeIds();
    if (ids.length) editor.deleteShapes(ids);
    showToast("已清空画布");
  }, [busy, showToast]);

  const runGrowth = useCallback(async () => {
    const editor = editorRef.current;
    if (!editor || busy) return;
    setBusy(true);
    try {
      await runGrowthDemo(editor, storyCards, streamOpts);
      showToast(prefersReducedMotion ? "已渲染（已跳过动画）" : "已渲染并播放生长动效");
    } catch (e) {
      console.error(e);
      showToast("渲染失败（请看控制台）");
    } finally {
      setBusy(false);
    }
  }, [busy, prefersReducedMotion, storyCards, streamOpts, showToast]);

  // Auto-run once if canvas is empty-ish.
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const shapes = editor.getCurrentPageShapes();
    if (shapes.length > 0) return;
    void runGrowth();
  }, [runGrowth]);

  return (
    <div className="overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-[0_12px_30px_rgba(15,23,42,0.05)]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/70 px-3 py-2">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold text-slate-700">PPT 画布编辑（Tldraw）</p>
          <p className="mt-0.5 text-[11px] text-slate-500">可拖拽/修改；下方工具栏来自 Tldraw。</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={busy || readOnly}
            onClick={() => void runGrowth()}
            className="inline-flex h-8 items-center rounded-[10px] bg-violet-600 px-3 text-[12px] font-semibold text-white shadow-sm disabled:opacity-50"
          >
            {busy ? "生成中…" : "重新生长"}
          </button>
          <button
            type="button"
            disabled={busy || readOnly}
            onClick={clearCanvas}
            className="inline-flex h-8 items-center rounded-[10px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 disabled:opacity-50"
          >
            清空
          </button>
          {readOnly ? null : (
            <Link
              href={`/canvas?session=${encodeURIComponent(sessionId)}`}
              prefetch={false}
              className="inline-flex h-8 items-center rounded-[10px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700"
            >
              全屏打开
            </Link>
          )}
        </div>
      </div>

      {toast ? <div className="px-3 py-2 text-[12px] font-medium text-emerald-700">{toast}</div> : null}

      <div className="relative h-[520px] w-full bg-zinc-100">
        <div className={readOnly ? "pointer-events-none absolute inset-0" : "absolute inset-0"}>
          <Tldraw inferDarkMode={false} autoFocus persistenceKey={persistenceKey} onMount={onMount} className="h-full w-full" />
        </div>
        {readOnly ? (
          <div className="pointer-events-none absolute inset-0 grid place-items-center bg-white/30">
            <div className="rounded-[14px] border border-slate-200 bg-white/90 px-3 py-2 text-[12px] font-semibold text-slate-700 shadow-sm">
              只读观摩中（创建者可编辑）
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

