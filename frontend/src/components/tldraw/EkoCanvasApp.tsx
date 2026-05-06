"use client";

import type { Editor } from "@tldraw/editor";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";

import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { fetchCanvasSessionMeta } from "@/lib/canvas/fetch-session-meta";
import { runGrowthDemo } from "@/lib/tldraw/growth-storyboard";
import { storyCardsFromSessionQuery } from "@/lib/tldraw/story-cards-from-session";

const HINT_STORAGE_KEY = "eko-canvas-agent-hint-dismissed";

/** 版本后缀：若画布异常可 bump，避免持久化脏状态（IndexedDB）影响渲染 */
function persistenceKeyFor(sessionId: string | null) {
  return `eko-tldraw-v4-${sessionId ?? "sandbox"}`;
}

export function EkoCanvasApp() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");
  const persistenceKey = useMemo(() => persistenceKeyFor(sessionId), [sessionId]);
  const prefersReducedMotion = usePrefersReducedMotion();

  const storyCards = useMemo(() => storyCardsFromSessionQuery(sessionId), [sessionId]);

  const editorRef = useRef<Editor | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [hintVisible, setHintVisible] = useState(false);
  const [apiSessionTitle, setApiSessionTitle] = useState<string | null>(null);

  const backHref = sessionId ? `/sessions/${encodeURIComponent(sessionId)}` : "/sessions";

  useEffect(() => {
    if (!sessionId) return;
    let alive = true;
    void (async () => {
      const meta = await fetchCanvasSessionMeta(sessionId);
      if (!alive) return;
      setApiSessionTitle(meta?.title ?? null);
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

  const streamOpts = useMemo(
    () =>
      prefersReducedMotion
        ? {
            reducedMotion: true as const,
            mockWsMessageGapMs: 0,
            shapeRevealDurationMs: 1,
          }
        : {
            reducedMotion: false as const,
            mockWsMessageGapMs: 380,
            shapeRevealDurationMs: 520,
          },
    [prefersReducedMotion],
  );

  const onGrowth = useCallback(async () => {
    const editor = editorRef.current;
    if (!editor || busy) return;
    setBusy(true);
    try {
      await runGrowthDemo(editor, storyCards, streamOpts);
      queueMicrotask(() => {
        editor.zoomToFit({ animation: { duration: prefersReducedMotion ? 0 : 280 } });
      });
      showToast(
        prefersReducedMotion
          ? `已根据会话结构生成故事板（${storyCards.length} 节点 · 已跳过动画）`
          : `Tldraw 画布已更新（${storyCards.length} 笔）。若看不到图形，请再点一次「清空画布」后重试。`,
      );
    } catch (e) {
      console.error(e);
      showToast("生成失败，请打开控制台查看详情");
    } finally {
      setBusy(false);
    }
  }, [busy, prefersReducedMotion, showToast, storyCards, streamOpts]);

  const onClear = useCallback(() => {
    const editor = editorRef.current;
    if (!editor || busy) return;
    editor.selectAll();
    const ids = editor.getSelectedShapeIds();
    if (ids.length) editor.deleteShapes(ids);
    showToast("已清空当前页全部形状");
  }, [busy, showToast]);

  const onExport = useCallback(() => {
    const editor = editorRef.current;
    if (!editor) return;
    try {
      const snapshot = editor.getSnapshot();
      const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `eko-canvas-${sessionId ?? "export"}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("已导出 tldraw 快照 JSON");
    } catch (e) {
      console.error(e);
      showToast("导出失败");
    }
  }, [sessionId, showToast]);

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
            下方白色区域为 <strong className="text-white/80">无限画布</strong>（含底部工具栏）。右侧点
            <strong className="mx-0.5 font-semibold text-white/90">「Agent 生长演示」</strong>
            {sessionId ? (
              <span className="ml-2 rounded-md bg-white/10 px-1.5 py-0.5 font-mono text-[11px] text-violet-200">
                session={sessionId}
              </span>
            ) : null}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void onGrowth()}
            aria-describedby="agent-demo-help"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2.5 text-[14px] font-semibold text-white shadow-[0_10px_28px_rgba(139,92,246,0.35)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? (
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            ) : (
              <SparkIcon />
            )}
            Agent 生长演示
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onClear}
            className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-[13px] font-semibold text-white/85 transition hover:bg-white/10 disabled:opacity-50"
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

      <p id="agent-demo-help" className="relative z-40 shrink-0 border-b border-white/5 bg-[#0f172a] px-4 py-2 text-center text-[12px] text-white/45">
        底部应出现 Tldraw 工具栏（选择 / 手型 / 图形）。若只有空白，请先<strong className="text-white/70">硬刷新</strong>（⌘⇧R）或点「清空画布」后再运行演示。
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
              已接入官方 <code className="rounded bg-white/10 px-1 font-mono text-[11px]">tldraw</code> 组件；紫色「Agent 生长演示」在
              <strong className="text-white">最顶栏右侧</strong>。
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

function SparkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M10 2.5l1.8 4.9 5 1.4-5 1.4L10 14.8 8.2 10 3.2 8.6l5-1.4L10 2.5z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}
