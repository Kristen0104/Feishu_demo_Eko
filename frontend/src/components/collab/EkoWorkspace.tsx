"use client";

import type { Editor } from "@tldraw/editor";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";

import {
  COLLAB_EVENTS,
  type CollabEnvelope,
  type CollabEventName,
  type CollabSessionPayload,
  type CollabStatus,
} from "@/config/collab-protocol";

type WorkspaceMode = "preview" | "edit";
type RuntimeStatus = CollabStatus;

type EkoWorkspaceProps = {
  mode: WorkspaceMode;
};

export function EkoWorkspace({ mode }: EkoWorkspaceProps) {
  const searchParams = useSearchParams();
  const router = useRouter();

  const sessionId = searchParams.get("session") ?? "demo-session";
  const currentUserId = searchParams.get("user") ?? searchParams.get("viewer") ?? "";
  const queryOwnerId = searchParams.get("owner") ?? "";

  const editorRef = useRef<Editor | null>(null);
  const syncedSnapshotTextRef = useRef<string>("");
  const manualSyncTimerRef = useRef<number | null>(null);
  const channelRef = useRef<BroadcastChannel | null>(null);

  const [ownerId, setOwnerId] = useState<string>(queryOwnerId);
  const [status, setStatus] = useState<RuntimeStatus>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [title, setTitle] = useState<string>("Eko 协同工作区");
  const [sources, setSources] = useState<string[]>([]);
  const [wsLabel, setWsLabel] = useState<string>("local");
  const [aiCommand, setAiCommand] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [editorReadyTick, setEditorReadyTick] = useState(0);
  const [saveToast, setSaveToast] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const isAiGenerating = status === "ai_generating";
  const isDev = process.env.NODE_ENV !== "production";
  const storageKey = useMemo(() => `eko:session:${sessionId}`, [sessionId]);

  const isOwner = useMemo(() => {
    if (!ownerId) return mode === "edit";
    if (!currentUserId) return false;
    return ownerId === currentUserId;
  }, [ownerId, currentUserId, mode]);

  const previewHref = useMemo(() => {
    const q = new URLSearchParams();
    q.set("session", sessionId);
    if (currentUserId) q.set("user", currentUserId);
    if (ownerId) q.set("owner", ownerId);
    return `/preview?${q.toString()}`;
  }, [sessionId, currentUserId, ownerId]);

  const canvasHref = useMemo(() => {
    const q = new URLSearchParams();
    q.set("session", sessionId);
    if (currentUserId) q.set("user", currentUserId);
    if (ownerId) q.set("owner", ownerId);
    return `/canvas?${q.toString()}`;
  }, [sessionId, currentUserId, ownerId]);

  const applyCanvasSnapshot = useCallback((snapshot: unknown) => {
    const editor = editorRef.current;
    if (!editor || snapshot === undefined || snapshot === null) return;
    try {
      editor.loadSnapshot(snapshot as never);
      const nextText = JSON.stringify(snapshot);
      syncedSnapshotTextRef.current = nextText;
    } catch {
      // Ignore malformed snapshots.
    }
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw) as CollabSessionPayload & { title?: string };
      if (parsed.owner_id) setOwnerId(parsed.owner_id);
      if (parsed.status) setStatus(parsed.status);
      if (typeof parsed.progress === "number") setProgress(Math.max(0, Math.min(1, parsed.progress)));
      if (parsed.title) setTitle(parsed.title);
      if (Array.isArray(parsed.sources)) setSources(parsed.sources);
      if (parsed.canvas_data) applyCanvasSnapshot(parsed.canvas_data);
    } catch {
      /* ignore invalid local data */
    }
  }, [applyCanvasSnapshot, storageKey]);

  useEffect(() => {
    if (mode !== "edit") return;
    if (!ownerId || !currentUserId) return;
    if (!isOwner) router.replace(previewHref);
  }, [mode, ownerId, currentUserId, isOwner, router, previewHref]);

  const persistLocalState = useCallback(
    (payload: CollabSessionPayload & { title?: string }) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(payload));
      } catch {
        /* ignore storage limits */
      }
    },
    [storageKey],
  );

  const emitLocalEvent = useCallback((envelope: CollabEnvelope) => {
    if (channelRef.current) {
      channelRef.current.postMessage(envelope);
    }
  }, []);

  const handleCollabEvent = useCallback(
    (eventName: CollabEventName | undefined, payload: (CollabSessionPayload & { title?: string }) | undefined) => {
      if (!eventName) return;
      if (eventName === COLLAB_EVENTS.CANVAS_SYNC) {
        if (payload?.canvas_data) applyCanvasSnapshot(payload.canvas_data);
        if (payload) persistLocalState(payload);
        return;
      }
      if (eventName === COLLAB_EVENTS.STATUS_BUSY) {
        setStatus("ai_generating");
        persistLocalState({ status: "ai_generating", owner_id: ownerId });
        return;
      }
      if (eventName === COLLAB_EVENTS.STATUS_IDLE) {
        setStatus("idle");
        persistLocalState({ status: "idle", owner_id: ownerId });
        return;
      }
      if (eventName === COLLAB_EVENTS.SESSION_META) {
        if (payload?.owner_id) setOwnerId(payload.owner_id);
        if (payload?.status) setStatus(payload.status);
        if (typeof payload?.progress === "number") {
          setProgress(Math.max(0, Math.min(1, payload.progress)));
        }
        if (payload?.title) setTitle(payload.title);
        if (Array.isArray(payload?.sources)) setSources(payload.sources);
        if (payload) persistLocalState(payload);
      }
    },
    [applyCanvasSnapshot, ownerId, persistLocalState],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const ch = new BroadcastChannel(`eko-collab-${sessionId}`);
    channelRef.current = ch;
    setWsLabel("local-open");
    ch.onmessage = (event) => {
      const raw = event.data as CollabEnvelope;
      handleCollabEvent(raw.event, raw.payload as CollabSessionPayload & { title?: string });
    };
    return () => {
      channelRef.current = null;
      ch.close();
    };
  }, [handleCollabEvent, sessionId]);

  useEffect(() => {
    if (mode !== "edit") return;
    const editor = editorRef.current;
    if (!editor) return;

    const unsubscribe = editor.store.listen(() => {
      if (status === "ai_generating") return;
      if (manualSyncTimerRef.current) {
        window.clearTimeout(manualSyncTimerRef.current);
      }
      manualSyncTimerRef.current = window.setTimeout(() => {
        const liveEditor = editorRef.current;
        if (!liveEditor) return;
        const snapshot = liveEditor.getSnapshot();
        const snapshotText = JSON.stringify(snapshot);
        if (snapshotText === syncedSnapshotTextRef.current) return;
        syncedSnapshotTextRef.current = snapshotText;
        const payload: CollabSessionPayload & { session_id: string } = {
          session_id: sessionId,
          canvas_data: snapshot,
          owner_id: ownerId || currentUserId || "local-owner",
        };
        emitLocalEvent({
          event: COLLAB_EVENTS.MANUAL_UPDATE,
          payload,
        });
        emitLocalEvent({
          event: COLLAB_EVENTS.CANVAS_SYNC,
          payload,
        });
        persistLocalState(payload);
        handleCollabEvent(COLLAB_EVENTS.CANVAS_SYNC, payload);
        void payload;
      }, 500);
    });

    return () => {
      if (typeof unsubscribe === "function") {
        unsubscribe();
      }
      if (manualSyncTimerRef.current) {
        window.clearTimeout(manualSyncTimerRef.current);
        manualSyncTimerRef.current = null;
      }
    };
  }, [mode, sessionId, status, editorReadyTick, emitLocalEvent, ownerId, currentUserId, persistLocalState, handleCollabEvent]);

  const submitAiCommand = useCallback(() => {
    const content = aiCommand.trim();
    if (!content) return;
    setStatus("ai_generating");
    const payload = {
      session_id: sessionId,
      owner_id: ownerId || currentUserId || "local-owner",
      command: content,
      status: "ai_generating",
    } as CollabSessionPayload & { session_id: string; command: string };
    emitLocalEvent({
      event: COLLAB_EVENTS.AI_COMMAND,
      payload,
    });
    emitLocalEvent({ event: COLLAB_EVENTS.STATUS_BUSY, payload });
    persistLocalState(payload);
    window.setTimeout(() => {
      const snapshot = editorRef.current?.getSnapshot() ?? payload.canvas_data;
      const syncPayload = {
        ...payload,
        canvas_data: snapshot,
      };
      emitLocalEvent({ event: COLLAB_EVENTS.CANVAS_SYNC, payload: syncPayload });
      emitLocalEvent({ event: COLLAB_EVENTS.STATUS_IDLE, payload: { ...syncPayload, status: "idle" } });
      handleCollabEvent(COLLAB_EVENTS.CANVAS_SYNC, syncPayload);
      handleCollabEvent(COLLAB_EVENTS.STATUS_IDLE, { ...syncPayload, status: "idle" });
    }, 1200);
    setAiCommand("");
  }, [aiCommand, sessionId, emitLocalEvent, ownerId, currentUserId, persistLocalState, handleCollabEvent]);

  const saveToFeishu = useCallback(async () => {
    if (saving) return;
    setSaving(true);
    setSaveToast(null);
    window.setTimeout(() => {
      setSaveToast({ tone: "success", message: "已本地保存（演示模式）" });
      setSaving(false);
      window.setTimeout(() => setSaveToast(null), 2400);
    }, 400);
  }, [saving, sessionId]);

  const triggerMockEvent = useCallback(
    (eventName: CollabEventName) => {
      if (eventName === COLLAB_EVENTS.CANVAS_SYNC) {
        const snapshot = editorRef.current?.getSnapshot();
        handleCollabEvent(eventName, { canvas_data: snapshot });
        return;
      }
      handleCollabEvent(eventName, {});
    },
    [handleCollabEvent],
  );

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-[#0b1020] text-white">
      <header className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{title}</p>
          <p className="text-xs text-white/60">
            session: {sessionId} · ws: {wsLabel}
          </p>
        </div>
        {mode === "preview" ? (
          isOwner ? (
            <Link href={canvasHref} className="rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold hover:bg-violet-500">
              🎨 进入画板编辑
            </Link>
          ) : (
            <span className="rounded-lg border border-white/20 px-3 py-2 text-sm text-white/75">只读观摩中</span>
          )
        ) : (
          <button
            type="button"
            disabled={saving || isAiGenerating}
            onClick={() => void saveToFeishu()}
            className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold hover:bg-emerald-500 disabled:opacity-60"
          >
            {saving ? "保存中..." : "确认保存"}
          </button>
        )}
      </header>

      <div className="border-b border-white/10 px-4 py-2">
        <div className="h-2 w-full rounded-full bg-white/10">
          <div className="h-2 rounded-full bg-cyan-400 transition-all" style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
      </div>

      <div className={`flex min-h-0 flex-1 flex-col lg:flex-row ${mode === "edit" ? "pb-24 sm:pb-0" : ""}`}>
        <section
          className={`relative min-h-[320px] min-w-0 flex-1 ${
            mode === "preview" || (mode === "edit" && isAiGenerating) ? "pointer-events-none" : ""
          }`}
        >
          <Tldraw
            inferDarkMode
            persistenceKey={`eko-collab-${sessionId}`}
            autoFocus={mode === "edit"}
            onMount={(editor) => {
              editorRef.current = editor;
              setEditorReadyTick((value) => value + 1);
            }}
            className="absolute inset-0 h-full w-full"
          />
        </section>

        <aside
          className={`w-full border-t border-white/10 bg-[#111933] p-4 lg:w-80 lg:border-l lg:border-t-0 ${
            mode === "edit" ? "hidden lg:block" : ""
          }`}
        >
          <h2 className="text-sm font-semibold">参考信息源</h2>
          <ul className="mt-3 space-y-2 text-xs text-white/75">
            {(sources.length ? sources : ["群聊上下文", "RAG 文档片段"]).map((item) => (
              <li key={item} className="rounded-md border border-white/10 px-3 py-2">
                {item}
              </li>
            ))}
          </ul>
          {mode === "edit" ? (
            <div className="mt-4 text-xs text-white/65">移动端建议优先使用底部 AI 指令框；手动拖拽在小屏会自动弱化。</div>
          ) : null}
        </aside>
      </div>

      {mode === "edit" ? (
        <div
          className="fixed inset-x-3 bottom-3 z-40 rounded-xl border border-white/20 bg-[#0f172fcc] p-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] backdrop-blur sm:inset-x-6 sm:bottom-4 sm:pb-3"
          style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 0.75rem)" }}
        >
          <div className="flex items-center gap-2">
            <input
              value={aiCommand}
              onChange={(event) => setAiCommand(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") submitAiCommand();
              }}
              placeholder="输入 AI 指令，例如：把整体背景换成深色科技风"
              className="h-12 min-w-0 flex-1 rounded-lg border border-white/20 bg-[#111933] px-4 text-base text-white placeholder:text-white/40 outline-none sm:h-10 sm:px-3 sm:text-sm"
              disabled={isAiGenerating}
            />
            <button
              type="button"
              onClick={submitAiCommand}
              disabled={isAiGenerating}
              className="h-12 rounded-lg bg-violet-600 px-5 text-base font-semibold hover:bg-violet-500 disabled:opacity-60 sm:h-10 sm:px-4 sm:text-sm"
            >
              发送
            </button>
          </div>
        </div>
      ) : null}

      {mode === "edit" ? (
        <div className="pointer-events-none absolute inset-y-0 left-0 hidden w-14 bg-gradient-to-r from-black/15 to-transparent md:block" />
      ) : null}

      {saveToast ? (
        <div className="pointer-events-none absolute right-4 top-20 z-[60]">
          <div
            className={`rounded-lg border px-3 py-2 text-sm shadow-lg ${
              saveToast.tone === "success"
                ? "border-emerald-300/40 bg-emerald-500/20 text-emerald-50"
                : "border-rose-300/40 bg-rose-500/20 text-rose-50"
            }`}
          >
            {saveToast.message}
          </div>
        </div>
      ) : null}

      {mode === "edit" && isAiGenerating ? (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/55">
          <div className="rounded-xl border border-white/20 bg-[#131a33] px-5 py-3 text-sm font-medium text-white">
            创建者正在通过 AI 修改...
          </div>
        </div>
      ) : null}

      {isDev ? (
        <div className="absolute bottom-3 left-3 z-[70] rounded-lg border border-white/20 bg-[#111933e6] p-2 text-[11px] text-white/80 backdrop-blur">
          <p className="mb-1 font-semibold text-white/90">Dev 事件模拟</p>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => triggerMockEvent(COLLAB_EVENTS.STATUS_BUSY)}
              className="rounded bg-amber-500/80 px-2 py-1 text-white hover:bg-amber-500"
            >
              BUSY
            </button>
            <button
              type="button"
              onClick={() => triggerMockEvent(COLLAB_EVENTS.STATUS_IDLE)}
              className="rounded bg-emerald-600/80 px-2 py-1 text-white hover:bg-emerald-600"
            >
              IDLE
            </button>
            <button
              type="button"
              onClick={() => triggerMockEvent(COLLAB_EVENTS.CANVAS_SYNC)}
              className="rounded bg-sky-600/80 px-2 py-1 text-white hover:bg-sky-600"
            >
              CANVAS_SYNC
            </button>
          </div>
        </div>
      ) : null}

      {mode === "edit" ? null : (
        <div className="absolute left-4 top-20 z-20 rounded-md border border-white/20 bg-black/35 px-2 py-1 text-xs text-white/80">
          <Link href={previewHref}>/preview</Link>
        </div>
      )}

      {mode === "preview" ? (
        <div className="pointer-events-none absolute inset-0 z-10">
          <div className="absolute right-[-120px] top-[22%] rotate-[-24deg] select-none text-[64px] font-semibold tracking-[0.22em] text-white/5">
            PREVIEW
          </div>
          <div className="absolute left-6 bottom-5 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-[12px] text-white/70 backdrop-blur">
            只读观摩 · user={currentUserId || "viewer"} · owner={ownerId || "unknown"}
          </div>
        </div>
      ) : null}
    </div>
  );
}
