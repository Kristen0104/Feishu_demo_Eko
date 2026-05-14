"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AnimatePresence, motion } from "@/components/MotionShim";
import { detailDesignTokens } from "@/components/session-detail/designTokens";
import { AccentPill, HeaderBadge, StatusPill, cn } from "@/components/UiPrimitives";
import { TopSearchIcon } from "@/components/workspace/workspace-chrome";
import { getReadableSessionTitle } from "@/lib/session-title";
import { deleteSyncSession } from "@/lib/sync/delete-session";
import { fetchSyncSessions } from "@/lib/sync/fetch-sessions";
import { SessionFilter, useAppStore } from "@/store/app-store";
import { SessionItem, SessionParticipant, SessionStatus } from "@/types/session";

function ItemModeIcon({ kind, compact }: { kind: SessionItem["kind"]; compact?: boolean }) {
  const base = compact
    ? "grid h-8 w-8 shrink-0 place-items-center rounded-[10px] border text-[10px] font-semibold leading-none"
    : "grid h-10 w-10 shrink-0 place-items-center rounded-[14px] border text-[12px] font-semibold leading-none";
  if (kind === "chat") return <span className={cn(base, "border-emerald-200 bg-emerald-50 text-emerald-700")}>聊</span>;
  if (kind === "doc") return <span className={cn(base, "border-sky-200 bg-sky-50 text-sky-700")}>稿</span>;
  return <span className={cn(base, "border-violet-200 bg-violet-50 text-violet-700")}>布</span>;
}

function RelatedKindIcon({ tone }: { tone: "文稿" | "聊天" | "数据" }) {
  const common = { width: 18, height: 18, viewBox: "0 0 18 18", fill: "none", "aria-hidden": true } as const;
  if (tone === "文稿") {
    return (
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border border-sky-200/90 bg-sky-50 text-sky-600">
        <svg {...common}>
          <path d="M5 3.5h5.2L12.5 6.6V14.5H5V3.5Z" stroke="currentColor" strokeWidth="1.35" strokeLinejoin="round" />
          <path d="M10.2 3.5V6.8h3.2" stroke="currentColor" strokeWidth="1.35" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }
  if (tone === "聊天") {
    return (
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border border-emerald-200/90 bg-emerald-50 text-emerald-600">
        <svg {...common}>
          <rect x="3.2" y="4.2" width="11.6" height="8.6" rx="2.2" stroke="currentColor" strokeWidth="1.35" />
          <path d="M6.2 12.8L5.6 15.2L8.4 12.8" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border border-violet-200/90 bg-violet-50 text-violet-600">
      <svg {...common}>
        <path d="M4 12V6l5-2.2 5 2.2v6l-5 2.2-5-2.2Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" />
        <path d="M9 3.8V14.2M4 6l5 2.2 5-2.2" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      </svg>
    </span>
  );
}

function SourceIcon({ source, compact }: { source: SessionItem["source"]; compact?: boolean }) {
  if (source === "飞书") {
    return (
      <span
        className={cn(
          "inline-flex shrink-0 items-center justify-center rounded-[8px] bg-blue-50 font-semibold text-blue-600",
          compact ? "h-5 w-5 text-[9px]" : "h-6 w-6 text-[11px]",
        )}
      >
        飞
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-[8px] bg-slate-100 text-slate-500",
        compact ? "h-5 w-5 text-[8px]" : "h-6 w-6 text-[11px]",
      )}
    >
      IM
    </span>
  );
}

function statusToWorkflow(status: SessionStatus): "completed" | "running" | "pending" | "warning" {
  if (status === "已同步") return "completed";
  if (status === "进行中") return "running";
  if (status === "待处理") return "warning";
  return "pending";
}

function mapRemoteStatus(status: string): SessionStatus {
  const normalized = status.trim().toLowerCase();
  if (status === "已同步" || normalized === "completed" || normalized === "done" || normalized === "success") return "已同步";
  if (status === "进行中" || normalized === "running" || normalized === "processing" || normalized === "queued") return "进行中";
  if (status.includes("失败") || normalized === "failed" || normalized === "error" || normalized === "cancelled") return "待处理";
  if (status === "草稿" || status === "待处理") return status;
  return "进行中";
}

function formatUpdatedAt(timestamp: string): string {
  const parsed = Date.parse(timestamp);
  if (Number.isNaN(parsed)) return "刚刚";
  const date = new Date(parsed);
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

function makeLiveSessionItem(session: {
  session_id: string;
  source: string;
  title: string;
  summary: string;
  status: string;
  updated_at: string;
  intent?: string | null;
  artifact?: {
    kind?: string | null;
    intent?: string | null;
    title?: string | null;
    result_summary?: string | null;
    current_step?: string | null;
  } | null;
  messages?: Array<{
    role?: string | null;
    content?: string | null;
  }>;
  context_messages?: Array<{
    role?: string | null;
    content?: string | null;
  }>;
}): SessionItem {
  const source = session.source === "feishu" ? "飞书" : "IM";
  const status = mapRemoteStatus(session.status);
  const updatedAt = formatUpdatedAt(session.updated_at);
  const collaborator: SessionParticipant = { id: "eko-bot", name: "Eko Bot", initials: "EK" };
  const signal = (session.artifact?.kind || session.artifact?.intent || session.intent || "").trim().toLowerCase();
  const kind: SessionItem["kind"] = signal === "board" ? "canvas" : signal === "ppt" || signal === "docx" || signal === "presentation" ? "doc" : "chat";
  const kindLabel: SessionItem["kindLabel"] = kind === "canvas" ? "画布" : kind === "doc" ? "文稿" : "聊天";
  const title = getReadableSessionTitle(session);
  const summary = session.summary || "由飞书消息触发的新会话。";
  return {
    id: session.session_id,
    title,
    summary,
    source,
    kind,
    kindLabel,
    status,
    updatedAt,
    participants: [collaborator],
    preview: {
      id: session.session_id,
      title,
      source,
      startedAt: updatedAt,
      outputMode: kindLabel,
      status,
      syncedAt: updatedAt,
      summary,
      collaborators: [collaborator],
      relatedItems: [],
      activity: {
        id: `${session.session_id}:activity`,
        actor: "Eko Bot",
        action: "创建了新会话",
        time: "刚刚",
      },
    },
  };
}

function AvatarStack({ participants, compact }: { participants: SessionParticipant[]; compact?: boolean }) {
  return (
    <div className={cn("flex shrink-0 items-center", compact ? "gap-1" : "gap-1.5")}>
      <div className={cn("flex", compact ? "-space-x-1" : "-space-x-1.5")}>
        {participants.slice(0, 3).map((person, pIdx) => (
          <div
            key={`${person.id}-${pIdx}`}
            className={cn(
              "flex items-center justify-center rounded-full border-2 border-white bg-slate-100 font-semibold text-slate-700",
              compact ? "h-6 w-6 text-[9px]" : "h-7 w-7 text-[10px]",
            )}
          >
            {person.initials}
          </div>
        ))}
      </div>
      <span className={cn("whitespace-nowrap text-slate-500", compact ? "text-[11px]" : "text-[12px]")}>{participants.length} 人</span>
    </div>
  );
}

function KindPill({ kindLabel, kind, className }: Pick<SessionItem, "kindLabel" | "kind"> & { className?: string }) {
  const tone = kind === "chat" ? "chat" : kind === "doc" ? "doc" : "canvas";
  return (
    <AccentPill tone={tone} className={className}>
      {kindLabel}
    </AccentPill>
  );
}

type SortOrder = "recent" | "oldest" | "title";

const sortLabels: Record<SortOrder, string> = {
  recent: "最新优先",
  oldest: "最早优先",
  title: "标题优先",
};

function getSessionSearchText(item: SessionItem): string {
  return [item.title, item.summary, item.source, item.kindLabel, item.participants.map((person) => person.name).join(" ")]
    .join(" ")
    .toLowerCase();
}

function parseSessionTime(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function safeFilename(value: string): string {
  const name = value.replace(/[\\/:*?"<>|]/g, "_").trim();
  return name || "会话摘要";
}

function sortSessionItems(items: SessionItem[], order: SortOrder): SessionItem[] {
  const collator = new Intl.Collator("zh-Hans", { sensitivity: "base", numeric: true });
  return [...items].sort((left, right) => {
    if (order === "title") {
      return collator.compare(left.title, right.title) || parseSessionTime(right.updatedAt) - parseSessionTime(left.updatedAt);
    }
    const delta = parseSessionTime(right.updatedAt) - parseSessionTime(left.updatedAt);
    return order === "recent" ? delta : -delta || collator.compare(left.title, right.title);
  });
}

function getSectionSortAnchor(section: { items: SessionItem[] }, order: SortOrder): number {
  if (section.items.length === 0) return 0;
  const timestamps = section.items.map((item) => parseSessionTime(item.updatedAt));
  if (order === "oldest") return Math.min(...timestamps);
  if (order === "title") return Math.max(...timestamps);
  return Math.max(...timestamps);
}

export function SessionsWorkspace({
  initialSections = [],
}: {
  initialSections?: Array<{ title: string; items: SessionItem[] }>;
}) {
  const pathname = usePathname() ?? "";
  const [toast, setToast] = useState<string | null>(null);
  const [liveData, setLiveData] = useState<{ sections: Array<{ title: string; items: SessionItem[] }> }>({
    sections: initialSections,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState<SortOrder>("recent");
  const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(false);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedSessionIds, setSelectedSessionIds] = useState<string[]>([]);
  const [isDeleting, setIsDeleting] = useState(false);
  const selectedId = useAppStore((state) => state.selectedSessionId);
  const isDetailOpen = useAppStore((state) => state.isDetailOpen);
  const activeFilter = useAppStore((state) => state.activeFilter);
  const starredMap = useAppStore((state) => state.starredMap);
  const runtimeSessionMap = useAppStore((state) => state.runtimeSessionMap);
  const setActiveFilter = useAppStore((state) => state.setActiveFilter);
  const selectSession = useAppStore((state) => state.selectSession);
  const closeDetail = useAppStore((state) => state.closeDetail);
  const initializeStars = useAppStore((state) => state.initializeStars);
  const toggleStar = useAppStore((state) => state.toggleStar);
  const setRuntimeSessionPatch = useAppStore((state) => state.setRuntimeSessionPatch);
  const defaultId = liveData.sections[0]?.items[0]?.id ?? "";

  const filterOptions: Array<{ key: SessionFilter; label: string }> = [
    { key: "all", label: "全部" },
    { key: "chat", label: "聊天" },
    { key: "doc", label: "文稿" },
    { key: "canvas", label: "画布" },
    { key: "recent", label: "最近" },
    { key: "starred", label: "已加星标" },
  ];

  useEffect(() => {
    const seen = new Set<string>();
    for (const section of liveData.sections) {
      for (const item of section.items) {
        if (seen.has(item.id) || !item.title) continue;
        seen.add(item.id);
        setRuntimeSessionPatch(item.id, { title: item.title });
      }
    }
  }, [liveData.sections, setRuntimeSessionPatch]);

  useEffect(() => {
    const hasSelectedItem = liveData.sections.some((section) => section.items.some((item) => item.id === selectedId));
    if (defaultId && (!selectedId || !hasSelectedItem)) selectSession(defaultId);
  }, [defaultId, liveData.sections, selectSession, selectedId]);

  useEffect(() => {
    let cancelled = false;
    const syncRemoteSessions = async () => {
      const sessions = await fetchSyncSessions();
      if (cancelled || sessions.length === 0) return;
      const incomingIds = new Set(sessions.map((session) => session.session_id));
      const liveItems = sessions.map(makeLiveSessionItem);
      setLiveData((current) => {
        const sections = current.sections.map((section) => ({
          ...section,
          items: section.items.filter((item) => !incomingIds.has(item.id)),
        }));
        const todayIndex = sections.findIndex((section) => section.title === "今天");
        if (todayIndex >= 0) {
          sections[todayIndex] = {
            ...sections[todayIndex],
            items: [...liveItems, ...sections[todayIndex].items],
          };
        } else {
          sections.unshift({ title: "今天", items: liveItems });
        }
        return { ...current, sections };
      });
      const initial: Record<string, boolean> = {};
      for (const session of sessions) {
        initial[session.session_id] = false;
      }
      initializeStars(initial);
    };
    void syncRemoteSessions();
    const timer = window.setInterval(syncRemoteSessions, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [initializeStars, setActiveFilter]);

  const getRuntimeStatus = (item: SessionItem) => runtimeSessionMap[item.id]?.status ?? item.status;
  const getRuntimeUpdatedAt = (item: SessionItem) => runtimeSessionMap[item.id]?.updatedAt ?? item.updatedAt;
  const isStarred = useCallback(
    (item: SessionItem) => (item.id in starredMap ? starredMap[item.id] : Boolean(item.starred)),
    [starredMap],
  );
  const toggleStarred = (itemId: string) => {
    const current = Boolean(starredMap[itemId]);
    toggleStar(itemId);
    setToast(current ? "已取消星标" : "已加入星标");
  };

  const normalizedQuery = searchQuery.trim().toLowerCase();

  const filteredSections = useMemo(() => {
    const sectionItems = liveData.sections
      .map((section) => {
        const items = section.items
          .filter((item) => {
            if (activeFilter === "chat") return item.kind === "chat";
            if (activeFilter === "doc") return item.kind === "doc";
            if (activeFilter === "canvas") return item.kind === "canvas";
            if (activeFilter === "starred") return isStarred(item);
            if (activeFilter === "recent") return section.title !== "更早";
            return true;
          })
          .filter((item) => (normalizedQuery ? getSessionSearchText(item).includes(normalizedQuery) : true));

        return {
          ...section,
          items: sortSessionItems(items, sortOrder),
        };
      })
      .filter((section) => section.items.length > 0);

    const collator = new Intl.Collator("zh-Hans", { sensitivity: "base", numeric: true });
    return [...sectionItems].sort((left, right) => {
      if (sortOrder === "title") {
        return collator.compare(left.title, right.title) || getSectionSortAnchor(right, sortOrder) - getSectionSortAnchor(left, sortOrder);
      }
      const delta = getSectionSortAnchor(right, sortOrder) - getSectionSortAnchor(left, sortOrder);
      return sortOrder === "recent" ? delta : -delta || collator.compare(left.title, right.title);
    });
  }, [activeFilter, isStarred, liveData.sections, normalizedQuery, sortOrder]);

  const visibleSessionIds = useMemo(
    () => filteredSections.flatMap((section) => section.items.map((item) => item.id)),
    [filteredSections],
  );

  const isAllVisibleSelected = visibleSessionIds.length > 0 && visibleSessionIds.every((id) => selectedSessionIds.includes(id));

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 1800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const toggleSelection = (itemId: string) => {
    setSelectedSessionIds((current) =>
      current.includes(itemId) ? current.filter((id) => id !== itemId) : [...current, itemId],
    );
    setIsSelectionMode(true);
  };

  const selectAllVisible = () => {
    setSelectedSessionIds(isAllVisibleSelected ? [] : visibleSessionIds);
    setIsSelectionMode(true);
  };

  const clearSelection = () => {
    setSelectedSessionIds([]);
    setIsSelectionMode(false);
  };

  const exportSelectedPreview = async (item: SessionItem) => {
    const lines = [
      `会话：${item.preview.title}`,
      `模式：${item.preview.outputMode}`,
      `状态：${getRuntimeStatus(item)}`,
      `来源：${item.preview.source}`,
      `时间：${item.preview.startedAt}`,
      "",
      item.preview.summary || item.summary,
    ];
    const text = lines.join("\n");
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        setToast("已复制会话摘要");
        return;
      }
    } catch {
      // Fall through to local download when clipboard permission is unavailable.
    }
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeFilename(item.preview.title || item.title)}-摘要.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
    setToast("已导出会话摘要");
  };

  const deleteSelectedSessions = async () => {
    if (selectedSessionIds.length === 0 || isDeleting) return;
    const confirmed = window.confirm(`确认删除选中的 ${selectedSessionIds.length} 个会话吗？`);
    if (!confirmed) return;

    setIsDeleting(true);
    try {
      const results = await Promise.all(selectedSessionIds.map((sessionId) => deleteSyncSession(sessionId)));
      const deletedIds = selectedSessionIds.filter((sessionId, index) => results[index]);
      const deletedSet = new Set(deletedIds);
      const failedCount = selectedSessionIds.length - deletedIds.length;

      if (deletedIds.length > 0) {
        setLiveData((current) => ({
          ...current,
          sections: current.sections
            .map((section) => ({
              ...section,
              items: section.items.filter((item) => !deletedSet.has(item.id)),
            }))
            .filter((section) => section.items.length > 0),
        }));
      }

      if (deletedIds.includes(selectedId ?? "")) {
        const nextId = visibleSessionIds.find((id) => !deletedSet.has(id)) ?? "";
        if (nextId) {
          selectSession(nextId);
        }
      }

      setSelectedSessionIds([]);
      setIsSelectionMode(false);
      setToast(
        failedCount > 0
          ? `已删除 ${deletedIds.length} 个会话，${failedCount} 个删除失败`
          : `已删除 ${deletedIds.length} 个会话`,
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const selectedItem = useMemo(() => {
    if (!selectedId) return null;
    for (const section of filteredSections.length > 0 ? filteredSections : liveData.sections) {
      const match = section.items.find((item) => item.id === selectedId);
      if (match) return match;
    }
    for (const section of liveData.sections) {
      const match = section.items.find((item) => item.id === selectedId);
      if (match) return match;
    }
    return null;
  }, [filteredSections, liveData.sections, selectedId]);

  return (
    <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <AnimatePresence>
          {toast ? (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.98 }}
              className="pointer-events-none absolute left-1/2 top-8 z-50 -translate-x-1/2 rounded-full border border-blue-200 bg-blue-50 px-4 py-1.5 text-[12px] font-semibold text-blue-600 shadow-[0_10px_24px_rgba(37,99,235,0.16)]"
            >
              {toast}
            </motion.div>
          ) : null}
        </AnimatePresence>

        <div className={cn("grid min-h-0 min-w-0 flex-1 grid-cols-1", selectedItem && isDetailOpen ? "xl:grid-cols-[minmax(0,1fr)_388px]" : "xl:grid-cols-1")}>
          <motion.div layout className={cn("flex min-h-0 min-w-0 flex-1 flex-col bg-white", selectedItem && isDetailOpen ? "xl:border-r xl:border-slate-200/90" : "")}>
              <div className="shrink-0 bg-white px-3 pb-2.5 pt-2.5 sm:px-4">
                <div className="min-w-0 border-b border-slate-200/90 pb-2.5">
                  <h1 className="text-[17px] font-semibold leading-tight tracking-[-0.03em] text-slate-950">会话</h1>
                  <p className="mt-0.5 max-w-2xl text-[12px] leading-snug text-slate-500">
                    查看和管理从即时消息路由而来的不同会话，并进入聊天、文稿或画布输出。
                  </p>
                </div>
              </div>

              <div className="flex min-h-0 min-w-0 flex-1 flex-col">
                <div className="min-h-0 flex-1 space-y-2.5 overflow-y-auto px-3 py-2.5 pb-24 lg:pb-2.5">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <label className="flex h-10 min-w-0 basis-full items-center gap-2 rounded-[12px] border border-slate-200 bg-[#fafbfc] px-2.5 sm:h-9 sm:min-w-[220px] sm:basis-auto sm:flex-1">
                        <TopSearchIcon />
                        <input
                          type="search"
                          value={searchQuery}
                          onChange={(event) => setSearchQuery(event.target.value)}
                          placeholder="搜索会话标题、摘要、来源"
                          className="w-full bg-transparent text-[12px] text-slate-700 outline-none placeholder:text-slate-400"
                        />
                        {searchQuery ? (
                          <button
                            type="button"
                            onClick={() => setSearchQuery("")}
                            className="text-[12px] font-semibold text-slate-400 hover:text-slate-600"
                            aria-label="清空搜索"
                          >
                            ×
                          </button>
                        ) : null}
                      </label>
                      <button
                        type="button"
                        onClick={() => setIsFilterPanelOpen((current) => !current)}
                        className={cn(
                          "inline-flex h-10 items-center whitespace-nowrap rounded-[12px] border px-3 text-[12px] font-semibold transition sm:h-9",
                          isFilterPanelOpen || activeFilter !== "all"
                            ? "border-blue-300 bg-blue-50 text-blue-700"
                            : "border-slate-200 bg-white text-slate-700",
                        )}
                      >
                        筛选
                      </button>
                      <button
                        type="button"
                        onClick={() => setSortOrder((current) => (current === "recent" ? "oldest" : current === "oldest" ? "title" : "recent"))}
                        className="inline-flex h-10 items-center gap-0.5 whitespace-nowrap rounded-[12px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 sm:h-9"
                      >
                        {sortLabels[sortOrder]}
                        <span className="text-slate-400">⌄</span>
                      </button>
                      {isSelectionMode ? (
                        <>
                          <button
                            type="button"
                            onClick={selectAllVisible}
                            className="inline-flex h-10 items-center whitespace-nowrap rounded-[12px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 sm:h-9"
                          >
                            全选
                          </button>
                          <button
                            type="button"
                            onClick={deleteSelectedSessions}
                            disabled={isDeleting || selectedSessionIds.length === 0}
                            className={cn(
                              "inline-flex h-10 min-w-0 items-center whitespace-nowrap rounded-[12px] px-3 text-[12px] font-semibold transition sm:h-9",
                              isDeleting || selectedSessionIds.length === 0
                                ? "cursor-not-allowed border border-slate-200 bg-slate-100 text-slate-400"
                                : "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
                            )}
                          >
                            {isDeleting ? "删除中..." : `删除选中 (${selectedSessionIds.length})`}
                          </button>
                          <button
                            type="button"
                            onClick={clearSelection}
                            className="inline-flex h-10 items-center whitespace-nowrap rounded-[12px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 sm:h-9"
                          >
                            退出多选
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setIsSelectionMode(true)}
                          className="inline-flex h-10 items-center whitespace-nowrap rounded-[12px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700 sm:h-9"
                        >
                          多选删除
                        </button>
                      )}
                    </div>

                    {isFilterPanelOpen ? (
                      <div className="rounded-[16px] border border-slate-200 bg-white p-2.5 shadow-[0_12px_30px_rgba(15,23,42,0.08)]">
                        <div className="flex flex-wrap gap-1.5">
                          {filterOptions.map((option) => {
                            const active = activeFilter === option.key;
                            return (
                              <button
                                key={option.key}
                                type="button"
                                onClick={() => setActiveFilter(option.key)}
                                className="rounded-full"
                              >
                                <HeaderBadge tone={active ? "info" : "neutral"}>{option.label}</HeaderBadge>
                              </button>
                            );
                          })}
                        </div>
                        <div className="mt-2.5 flex items-center justify-between gap-2">
                          <p className="text-[12px] text-slate-500">
                            当前筛选：{filterOptions.find((option) => option.key === activeFilter)?.label ?? "全部"}
                          </p>
                          <button
                            type="button"
                            onClick={() => setActiveFilter("all")}
                            className="text-[12px] font-semibold text-blue-600 hover:text-blue-700"
                          >
                            重置筛选
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="flex origin-left scale-[0.94] flex-wrap gap-1.5">
                    {filterOptions.map((option) => {
                      const active = activeFilter === option.key;
                      return (
                        <button key={option.key} type="button" onClick={() => setActiveFilter(option.key)} className="rounded-full">
                          <HeaderBadge tone={active ? "info" : "neutral"}>{option.label}</HeaderBadge>
                        </button>
                      );
                    })}
                  </div>

                  <div className="space-y-3 pb-1">
                    {filteredSections.length === 0 ? (
                      <div className="rounded-[14px] border border-slate-200/90 bg-[#fafbfc] px-4 py-6 text-center text-[13px] text-slate-500">
                        {searchQuery ? "没有找到匹配的会话，试试清空搜索条件。" : "当前筛选暂无会话，试试切换到“全部”。"}
                      </div>
                    ) : null}
                    {filteredSections.map((section) => (
                      <div key={section.title}>
                        <h3 className="pb-1.5 text-[12px] font-semibold uppercase tracking-wide text-slate-500">{section.title}</h3>
                        <div className="space-y-1.5">
                          {section.items.map((item) => {
                            const sessionHref = `/sessions/${encodeURIComponent(item.id)}`;
                            const routeActive = pathname === sessionHref;
                            const active = routeActive || selectedItem?.id === item.id;
                            const checked = selectedSessionIds.includes(item.id);
                            const rowClasses = cn(
                              "flex w-full items-start gap-2.5 rounded-[14px] border px-3 py-2.5 text-left transition outline-none ring-offset-2 focus-visible:ring-2 focus-visible:ring-blue-500 sm:gap-2 sm:px-2.5 sm:py-2",
                              active
                                ? "border-blue-300/90 bg-blue-50/80 shadow-[0_4px_14px_rgba(37,99,235,0.08)]"
                                : "border-slate-200/90 bg-[#fafbfc] hover:border-slate-300 hover:bg-white",
                            );
                            const rowContent = (
                              <>
                                {isSelectionMode ? (
                                  <span className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-[6px] border border-slate-300 bg-white">
                                    <input
                                      type="checkbox"
                                      checked={checked}
                                      onChange={() => toggleSelection(item.id)}
                                      onClick={(event) => event.stopPropagation()}
                                      className="h-3.5 w-3.5 accent-blue-600"
                                      aria-label={`选择 ${item.title}`}
                                    />
                                  </span>
                                ) : null}
                                <ItemModeIcon kind={item.kind} compact />
                                <div className="grid min-w-0 flex-1 grid-cols-1 gap-y-2 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] sm:items-start sm:gap-x-3 sm:gap-y-1">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1">
                                      <h4 className="truncate text-[13px] font-semibold leading-tight text-slate-900">{item.title}</h4>
                                      {isSelectionMode ? null : (
                                        <button
                                          type="button"
                                          onClick={(event) => {
                                            event.preventDefault();
                                            event.stopPropagation();
                                            toggleStarred(item.id);
                                          }}
                                          className={cn(
                                            "shrink-0 text-[11px] transition",
                                            isStarred(item) ? "text-amber-400 hover:text-amber-500" : "text-slate-300 hover:text-slate-500",
                                          )}
                                          aria-label={isStarred(item) ? "取消星标" : "设为星标"}
                                        >
                                          {isStarred(item) ? "★" : "☆"}
                                        </button>
                                      )}
                                    </div>
                                    <p className="mt-0.5 line-clamp-1 text-[11px] leading-snug text-slate-500">{item.summary}</p>
                                  </div>
                                  <div className="flex max-w-full flex-wrap items-center justify-start gap-1 self-start px-0.5 pt-0.5 sm:justify-center">
                                    <div className="flex items-center gap-0.5 text-[11px] text-slate-600">
                                      <SourceIcon source={item.source} compact />
                                      <span className="max-w-[4rem] truncate">{item.source}</span>
                                    </div>
                                    <KindPill kind={item.kind} kindLabel={item.kindLabel} className="!min-h-6 px-2 py-0.5 text-[10px]" />
                                    <StatusPill status={statusToWorkflow(getRuntimeStatus(item))}>
                                      <span className="text-[10px]">{getRuntimeStatus(item)}</span>
                                    </StatusPill>
                                  </div>
                                  <div className="flex flex-row flex-wrap items-center justify-between gap-2 pt-0.5 sm:flex-col sm:items-end sm:gap-1 sm:justify-self-end">
                                    <span className="text-[11px] tabular-nums text-slate-400">{getRuntimeUpdatedAt(item)}</span>
                                    <AvatarStack participants={item.participants} compact />
                                  </div>
                                </div>
                              </>
                            );
                            return (
                              isSelectionMode ? (
                                <div key={item.id} className={rowClasses} onClick={() => toggleSelection(item.id)}>
                                  {rowContent}
                                </div>
                              ) : (
                                <Link
                                  key={item.id}
                                  href={sessionHref}
                                  prefetch={false}
                                  scroll
                                  onClick={() => selectSession(item.id)}
                                  className={rowClasses}
                                >
                                  {rowContent}
                                </Link>
                              )
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>

          <AnimatePresence mode="wait">
              {selectedItem && isDetailOpen ? (
                <motion.div
                  key="session-detail-panel"
                  initial={{ opacity: 0, x: 28 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="hidden min-h-0 min-w-0 flex-col bg-white px-3 pb-3 pt-2.5 xl:flex xl:pl-4 xl:pr-4"
                >
                  <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[24px] border border-slate-200/90 bg-white shadow-[0_10px_40px_rgba(15,23,42,0.06)]">
                  <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 xl:px-6 xl:py-6">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <h2 className="text-[18px] font-semibold leading-snug tracking-[-0.03em] text-slate-950">
                            {selectedItem.preview.title}
                          </h2>
                          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[12px] leading-snug text-slate-500">
                            <div className="flex items-center gap-1.5">
                              <SourceIcon source={selectedItem.preview.source} compact />
                              <span className="text-slate-600">{selectedItem.preview.source}</span>
                            </div>
                            <span className="text-slate-300">|</span>
                            <span>{selectedItem.preview.startedAt}</span>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-0.5">
                          <button
                            type="button"
                            onClick={() => toggleStarred(selectedItem.id)}
                            className={cn(
                              "flex h-9 w-9 items-center justify-center rounded-lg text-[18px] transition hover:bg-slate-50",
                              isStarred(selectedItem) ? "text-amber-400 hover:text-amber-500" : "text-slate-400 hover:text-slate-600",
                            )}
                            aria-label={isStarred(selectedItem) ? "取消星标" : "设为星标"}
                          >
                            {isStarred(selectedItem) ? "★" : "☆"}
                          </button>
                          <button
                            type="button"
                            onClick={closeDetail}
                            className="flex h-9 w-9 items-center justify-center rounded-lg text-[22px] leading-none text-slate-400 transition hover:bg-slate-50 hover:text-slate-600"
                            aria-label="关闭"
                          >
                            ×
                          </button>
                        </div>
                      </div>

                      <div className="mt-5 flex flex-wrap gap-2">
                        <Link
                          href={`/sessions/${encodeURIComponent(selectedItem.id)}`}
                          className={cn(detailDesignTokens.button.primary, "min-w-[120px] flex-1 justify-center sm:flex-none")}
                        >
                          打开
                        </Link>
                        <Link
                          href={`/sessions/${encodeURIComponent(selectedItem.id)}`}
                          prefetch={false}
                          className={cn(detailDesignTokens.button.control, "min-w-[120px] flex-1 justify-center sm:flex-none")}
                        >
                          继续
                        </Link>
                        <button
                          type="button"
                          onClick={() => void exportSelectedPreview(selectedItem)}
                          className={cn(detailDesignTokens.button.control, "gap-1")}
                        >
                          导出 <span className="text-slate-400">↗</span>
                        </button>
                      </div>

                      <dl className="mt-5 space-y-2.5 text-[12px] text-slate-600">
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-slate-500">输出模式</dt>
                      <dd>
                        <KindPill kind={selectedItem.kind} kindLabel={selectedItem.preview.outputMode} />
                      </dd>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-slate-500">状态</dt>
                      <dd>
                        <StatusPill status={statusToWorkflow(getRuntimeStatus(selectedItem))}>{getRuntimeStatus(selectedItem)}</StatusPill>
                      </dd>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-slate-500">来源</dt>
                      <dd className="flex items-center gap-2 font-medium text-slate-800">
                        <SourceIcon source={selectedItem.preview.source} />
                        {selectedItem.preview.source}
                      </dd>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <dt className="text-slate-500">最近同步</dt>
                      <dd className="font-medium text-slate-800">{selectedItem.preview.syncedAt}</dd>
                    </div>
                    <div className="flex items-start justify-between gap-4">
                      <dt className="pt-0.5 text-slate-500">协作者</dt>
                      <dd>
                        <div className="flex -space-x-2">
                          {selectedItem.preview.collaborators.map((person, cIdx) => (
                            <div
                              key={`${person.id}-${cIdx}`}
                              className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-slate-100 text-[11px] font-semibold text-slate-700"
                            >
                              {person.initials}
                            </div>
                          ))}
                        </div>
                      </dd>
                    </div>
                  </dl>

                      <div className="mt-6">
                        <h3 className="text-[15px] font-semibold tracking-[-0.02em] text-slate-950">摘要</h3>
                        <p className="mt-2 text-[12px] leading-[1.65] text-slate-600">{selectedItem.preview.summary}</p>
                      </div>

                      <div className="mt-6">
                        <h3 className="text-[15px] font-semibold tracking-[-0.02em] text-slate-950">相关内容</h3>
                        <ul className="mt-3 space-y-2">
                          {selectedItem.preview.relatedItems.map((rel) => (
                            <li
                              key={rel.id}
                              className="flex items-start gap-3 rounded-[14px] border border-slate-200/80 bg-slate-50/40 px-3 py-2.5 transition hover:border-slate-300/90 hover:bg-white"
                            >
                              <RelatedKindIcon tone={rel.tone} />
                              <div className="min-w-0 flex-1 pt-0.5">
                                <div className="flex items-start justify-between gap-2">
                                  <p className="min-w-0 flex-1 text-[13px] font-semibold leading-snug text-slate-900">{rel.title}</p>
                                  <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200/80">
                                    {rel.tone}
                                  </span>
                                </div>
                                <p className="mt-1 text-[11px] text-slate-500">{rel.updatedAt}</p>
                              </div>
                            </li>
                          ))}
                        </ul>

                        <div className="mt-6 border-t border-slate-100 pt-5">
                          <h3 className="text-[15px] font-semibold tracking-[-0.02em] text-slate-950">活动</h3>
                          <div className="mt-3 flex items-center justify-between gap-2 rounded-[14px] border border-slate-200/80 bg-slate-50/40 px-3 py-2.5">
                            <div className="flex min-w-0 items-center gap-2.5">
                              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-200/90 text-[11px] font-semibold text-slate-700">
                                {selectedItem.preview.activity.actor
                                  .split(" ")
                                  .map((p) => p[0])
                                  .join("")
                                  .slice(0, 2)}
                              </div>
                              <p className="min-w-0 text-[13px] text-slate-700">
                                <span className="font-semibold text-slate-900">{selectedItem.preview.activity.actor}</span>
                                <span className="ml-1">{selectedItem.preview.activity.action}</span>
                              </p>
                            </div>
                            <span className="shrink-0 whitespace-nowrap text-[12px] text-slate-500">{selectedItem.preview.activity.time}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ) : null}
          </AnimatePresence>
        </div>
      </div>
  );
}
