"use client";

import type { Editor } from "@tldraw/editor";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";

import { fetchCanvasSessionMeta } from "@/lib/canvas/fetch-session-meta";
import { getReadableSessionTitle, looksLikeTechnicalSessionTitle } from "@/lib/session-title";

const HINT_STORAGE_KEY = "eko-canvas-agent-hint-dismissed";

/** 版本后缀：若画布异常可 bump，避免持久化脏状态（IndexedDB）影响渲染 */
function persistenceKeyFor(sessionId: string | null) {
  return `eko-tldraw-v4-${sessionId ?? "sandbox"}`;
}

export function EkoCanvasApp() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");
  const persistenceKey = useMemo(() => persistenceKeyFor(sessionId), [sessionId]);

  const editorRef = useRef<Editor | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [hintVisible, setHintVisible] = useState(false);
  const [apiSessionTitle, setApiSessionTitle] = useState<string | null>(null);

  const backHref = sessionId ? `/sessions/${encodeURIComponent(sessionId)}` : "/sessions";
  const canvasFileName = useMemo(() => {
    const base = apiSessionTitle?.trim() && !looksLikeTechnicalSessionTitle(apiSessionTitle) ? apiSessionTitle.trim() : "Eko 画布";
    return `${base.replace(/[\\/:*?"<>|]/g, "_")}.json`;
  }, [apiSessionTitle]);

  useEffect(() => {
    if (!sessionId) return;
    let alive = true;
    void (async () => {
      const meta = await fetchCanvasSessionMeta(sessionId);
      if (!alive) return;
      setApiSessionTitle(meta ? getReadableSessionTitle({ session_id: meta.session_id, title: meta.title, intent: meta.mode }) : null);
    })();
    return () => {
      alive = false;
    };
  }, [sessionId]);

  useEffect(() => {
    try {
      const dismissed = sessionStorage.getItem(HINT_STORAGE_KEY);
      queueMicrotask(() => setHintVisible(!dismissed));
    } catch {
      queueMicrotask(() => setHintVisible(true));
    }
  }, []);

  const dismissHint = useCallback(() => {
    try {
      sessionStorage.setItem(HINT_STORAGE_KEY, "1");
    } catch {
      /* ignore */
    }
    setHintVisible(false);
  }, []);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 3800);
  }, []);

  const onMount = useCallback((editor: Editor) => {
    editorRef.current = editor;
    editor.user.updateUserPreferences({ colorScheme: "light" });
    queueMicrotask(() => {
      editor.zoomToFit({ animation: { duration: 0 } });
    });
    return () => {
      editorRef.current = null;
    };
  }, []);

  const onClear = useCallback(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.selectAll();
    const ids = editor.getSelectedShapeIds();
    if (ids.length) editor.deleteShapes(ids);
    showToast("已清空当前页全部形状");
  }, [showToast]);

  const onExport = useCallback(() => {
    const editor = editorRef.current;
    if (!editor) return;
    try {
      const snapshot = editor.getSnapshot();
      const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = canvasFileName;
      a.click();
      URL.revokeObjectURL(url);
      showToast("已导出 tldraw 快照 JSON");
    } catch (e) {
      console.error(e);
      showToast("导出失败");
    }
  }, [canvasFileName, showToast]);

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0b1220]">
      <header className="relative z-50 flex shrink-0 flex-wrap items-center gap-3 border-b border-white/10 bg-[#0b1220]/95 px-4 py-3 text-white shadow-[0_8px_32px_rgba(0,0,0,0.35)] backdrop-blur-md">
        <Link
          href={backHref}
          prefetch={false}
          className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-[13px] font-semibold text-white/90 transition hover:bg-white/10"
        >
          <span aria-hidden>←</span>
          返回会话
        </Link>

        <div className="hidden h-8 w-px bg-white/15 sm:block" />

        <div className="min-w-0 flex-1">
          <h1 className="truncate text-[15px] font-semibold tracking-tight text-white">
            Eko 画布 · Tldraw
            {sessionId && apiSessionTitle ? (
              <span className="ml-2 font-normal text-white/70">· {apiSessionTitle}</span>
            ) : null}
          </h1>
          <p className="truncate text-[12px] text-white/55">
            下方白色区域为 <strong className="text-white/80">无限画布</strong>（含底部工具栏）。
            {sessionId ? (
              <span className="ml-2 rounded-md bg-white/10 px-1.5 py-0.5 text-[11px] text-violet-100">
                已关联会话
              </span>
            ) : null}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onClear}
            className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-[13px] font-semibold text-white/85 transition hover:bg-white/10"
          >
            清空画布
          </button>
          <button
            type="button"
            onClick={onExport}
            className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-[13px] font-semibold text-white/85 transition hover:bg-white/10"
          >
            导出 JSON
          </button>
        </div>
      </header>

      <p id="agent-canvas-help" className="relative z-40 shrink-0 border-b border-white/5 bg-[#0f172a] px-4 py-2 text-center text-[12px] text-white/45">
        底部应出现 Tldraw 工具栏（选择 / 手型 / 图形）。画布内容会保存到当前浏览器的会话工作区。
      </p>

      {toast ? (
        <div className="relative z-50 mx-auto shrink-0 px-4 py-2">
          <div className="rounded-xl border border-emerald-400/25 bg-emerald-500/15 px-4 py-2 text-center text-[13px] font-medium text-emerald-50 shadow-lg">
            {toast}
          </div>
        </div>
      ) : null}

      {/* 关键：overflow-hidden + min-h-0 让 flex 子项获得确定高度，Tldraw 才能铺满；勿在画布上方叠 z-index 过高的 fixed 层，否则会挡住 Tldraw 底部 UI（z~300） */}
      <div className="relative z-0 min-h-0 min-w-0 flex-1 overflow-hidden bg-zinc-100">
        <Tldraw
          inferDarkMode={false}
          autoFocus
          persistenceKey={persistenceKey}
          onMount={onMount}
          className="absolute inset-0 h-full w-full"
        />

        {hintVisible ? (
          <div className="pointer-events-none absolute right-3 top-3 z-[1] max-w-[min(340px,calc(100%-1.5rem))] rounded-xl border border-violet-400/40 bg-[#1e1b4b]/90 px-3 py-2 text-[12px] leading-snug text-violet-50 shadow-lg backdrop-blur-md">
            <p className="pointer-events-auto font-semibold text-white">提示</p>
            <p className="pointer-events-auto mt-1 text-white/90">
              已接入官方 <code className="rounded bg-white/10 px-1 font-mono text-[11px]">tldraw</code> 组件，可直接绘制、整理和导出当前画布。
            </p>
            <button
              type="button"
              onClick={dismissHint}
              className="pointer-events-auto mt-2 w-full rounded-lg bg-white/15 py-1.5 text-[11px] font-semibold text-white hover:bg-white/20"
            >
              知道了
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
