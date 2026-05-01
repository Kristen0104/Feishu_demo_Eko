"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AnimatePresence, motion } from "@/components/MotionShim";
import { detailDesignTokens } from "@/components/session-detail/designTokens";
import { AccentPill, HeaderBadge, StatusPill, cn } from "@/components/UiPrimitives";
import { useMockWebSocket } from "@/hooks/useMockWebSocket";
import { SessionFilter, useAppStore } from "@/store/app-store";
import { SessionItem, SessionListPageData, SessionParticipant, SessionStatus } from "@/types/session";

function TopSearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="5.5" stroke="#64748B" strokeWidth="1.5" />
      <path d="M12.5 12.5L16 16" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function HelpIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="10" r="8.2" stroke="#0F172A" strokeWidth="1.5" />
      <path
        d="M7.9 7.8C7.9 6.63 8.88 5.8 10.1 5.8C11.23 5.8 12.1 6.46 12.1 7.56C12.1 8.4 11.66 8.87 10.97 9.28C10.22 9.73 9.9 10.09 9.9 10.9"
        stroke="#0F172A"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="10" cy="13.7" r="0.9" fill="#0F172A" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M6.2 7.7C6.2 5.6 7.9 3.9 10 3.9C12.1 3.9 13.8 5.6 13.8 7.7V9.5C13.8 10.45 14.11 11.38 14.69 12.13L15.4 13.05C15.82 13.6 15.43 14.4 14.74 14.4H5.26C4.57 14.4 4.18 13.6 4.6 13.05L5.31 12.13C5.89 11.38 6.2 10.45 6.2 9.5V7.7Z"
        stroke="#0F172A"
        strokeWidth="1.5"
      />
      <path d="M8.3 15.2C8.55 16.11 9.2 16.7 10 16.7C10.8 16.7 11.45 16.11 11.7 15.2" stroke="#0F172A" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function SessionsListTopBar({ teamName, teamMembersLabel, userInitials }: { teamName: string; teamMembersLabel: string; userInitials: string }) {
  return (
    <div className="flex h-[72px] shrink-0 items-center justify-between border-b border-slate-200/90 px-6">
      <div className="flex min-w-0 items-center gap-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-blue-600 text-[21px] font-bold text-white shadow-[0_8px_20px_rgba(37,99,235,0.22)]">
            e
          </div>
          <span className="text-[16px] font-semibold tracking-[-0.04em] text-slate-950">Eko</span>
        </div>
        <div className="hidden min-w-0 items-center gap-3 text-[14px] text-slate-500 xl:flex">
          <span>Eko</span>
          <span className="text-slate-300">/</span>
          <span className="font-semibold text-slate-800">会话</span>
        </div>
      </div>
      <div className="flex min-w-0 flex-1 items-center justify-end gap-3 pl-3">
        <div className="hidden h-10 min-w-0 max-w-[min(332px,42vw)] flex-1 items-center gap-3 rounded-[15px] border border-slate-200 bg-white px-4 shadow-[0_4px_12px_rgba(15,23,42,0.03)] lg:flex">
          <TopSearchIcon />
          <span className="min-w-0 flex-1 truncate text-[14px] text-slate-400">搜索（⌘K）</span>
        </div>
        <button
          type="button"
          className="hidden min-w-[170px] max-w-[220px] shrink-0 items-center justify-between gap-2 rounded-[16px] border border-slate-200 bg-white px-3 py-2.5 text-left shadow-[0_4px_12px_rgba(15,23,42,0.03)] xl:flex"
        >
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[12px] bg-blue-50 text-blue-600">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path
                  d="M3 5.2L8.4 2.8L15 5.7L9.6 8.1L3 5.2Z"
                  fill="currentColor"
                  fillOpacity="0.18"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  strokeLinejoin="round"
                />
                <path d="M3.1 5.7V11.6L9.1 14.3V8.4" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                <path d="M15 5.7V11.2L9.1 14.3" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="truncate text-[14px] font-semibold text-slate-800">{teamName}</p>
              <p className="truncate text-[12px] text-slate-500">{teamMembersLabel}</p>
            </div>
          </div>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="shrink-0">
            <path d="M4.5 6.5L8 10L11.5 6.5" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <button
          type="button"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.03)]"
          aria-label="帮助"
        >
          <HelpIcon />
        </button>
        <button
          type="button"
          className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.03)]"
          aria-label="通知"
        >
          <BellIcon />
          <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold leading-none text-white">
            1
          </span>
        </button>
        <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[14px] font-semibold text-slate-700 shadow-[0_4px_12px_rgba(15,23,42,0.03)]">
          {userInitials}
          <span className="absolute bottom-0.5 right-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-500" />
        </div>
      </div>
    </div>
  );
}

function NavIcon({ type, active }: { type: "home" | "chat" | "doc" | "canvas" | "agents" | "settings"; active?: boolean }) {
  const stroke = active ? "#2563EB" : "#475569";
  const common = { width: 20, height: 20, viewBox: "0 0 20 20", fill: "none", "aria-hidden": true } as const;
  switch (type) {
    case "home":
      return (
        <svg {...common}>
          <path d="M3 8.5L10 3L17 8.5V16.2H12.5V11.2H7.5V16.2H3V8.5Z" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      );
    case "chat":
      return (
        <svg {...common}>
          <rect x="3" y="3.5" width="14" height="10.5" rx="3" stroke={stroke} strokeWidth="1.6" />
          <path d="M7 14L6.3 17L9.5 14" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "doc":
      return (
        <svg {...common}>
          <path d="M6 2.8H12.2L15.8 6.4V17.2H6V2.8Z" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" />
          <path d="M12 2.8V6.6H15.8" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      );
    case "canvas":
      return (
        <svg {...common}>
          <rect x="3.2" y="3.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
          <rect x="11.2" y="3.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
          <rect x="3.2" y="11.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
          <rect x="11.2" y="11.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
        </svg>
      );
    case "agents":
      return (
        <svg {...common}>
          <rect x="6.2" y="3.5" width="7.6" height="5.8" rx="2.2" stroke={stroke} strokeWidth="1.6" />
          <path d="M5.4 16.2C5.7 13.7 7.6 12.4 10 12.4C12.4 12.4 14.3 13.7 14.6 16.2" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M4.2 7.4H2.8" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M17.2 7.4H15.8" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <circle cx="10" cy="10" r="6.5" stroke={stroke} strokeWidth="1.6" />
          <path d="M10 6.8V13.2" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M6.8 10H13.2" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
  }
}

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
  return "pending";
}

function AvatarStack({ participants, compact }: { participants: SessionParticipant[]; compact?: boolean }) {
  return (
    <div className={cn("flex shrink-0 items-center", compact ? "gap-1" : "gap-1.5")}>
      <div className={cn("flex", compact ? "-space-x-1" : "-space-x-1.5")}>
        {participants.slice(0, 3).map((person) => (
          <div
            key={person.id}
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

export function SessionsWorkspace({ data }: { data: SessionListPageData }) {
  const defaultId = data.sections[0]?.items[0]?.id ?? "";
  const [toast, setToast] = useState<string | null>(null);
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

  const filterOptions: Array<{ key: SessionFilter; label: string }> = [
    { key: "all", label: "全部" },
    { key: "chat", label: "聊天" },
    { key: "doc", label: "文稿" },
    { key: "canvas", label: "画布" },
    { key: "recent", label: "最近" },
    { key: "starred", label: "已加星标" },
  ];

  useEffect(() => {
    if (!selectedId && defaultId) selectSession(defaultId);
  }, [defaultId, selectSession, selectedId]);

  useEffect(() => {
    const initial: Record<string, boolean> = {};
    for (const section of data.sections) {
      for (const item of section.items) {
        initial[item.id] = Boolean(item.starred);
      }
    }
    initializeStars(initial);
  }, [data.sections, initializeStars]);

  const allItems = useMemo(() => data.sections.flatMap((section) => section.items), [data.sections]);

  useMockWebSocket({
    enabled: allItems.length > 0,
    intervalMs: 9000,
    onTick: () => {
      const targets = allItems.map((item) => item.id);
      if (!targets.length) return;
      const now = new Date();
      const minuteSeed = now.getMinutes() + now.getSeconds();
      const index = minuteSeed % targets.length;
      const statuses: SessionStatus[] = ["进行中", "已同步", "待处理", "草稿"];
      const id = targets[index];
      const next = statuses[minuteSeed % statuses.length];
      const updatedAt = `刚刚 ${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
      setRuntimeSessionPatch(id, { status: next, updatedAt });
    },
  });

  const getRuntimeStatus = (item: SessionItem) => runtimeSessionMap[item.id]?.status ?? item.status;
  const getRuntimeUpdatedAt = (item: SessionItem) => runtimeSessionMap[item.id]?.updatedAt ?? item.updatedAt;
  const isStarred = (item: SessionItem) => (item.id in starredMap ? starredMap[item.id] : Boolean(item.starred));
  const toggleStarred = (itemId: string) => {
    const current = Boolean(starredMap[itemId]);
    toggleStar(itemId);
    setToast(current ? "已取消星标" : "已加入星标");
  };

  const matchesFilter = (item: SessionItem, sectionTitle: string) => {
    if (activeFilter === "all") return true;
    if (activeFilter === "chat") return item.kind === "chat";
    if (activeFilter === "doc") return item.kind === "doc";
    if (activeFilter === "canvas") return item.kind === "canvas";
    if (activeFilter === "starred") return isStarred(item);
    return sectionTitle === "今天";
  };

  const filteredSections = useMemo(
    () =>
      data.sections
        .map((section) => ({
          ...section,
          items: section.items.filter((item) => matchesFilter(item, section.title)),
        }))
        .filter((section) => section.items.length > 0),
    [data.sections, activeFilter],
  );

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 1800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const selectedItem = useMemo(() => {
    if (!selectedId) return null;
    for (const section of filteredSections.length > 0 ? filteredSections : data.sections) {
      const match = section.items.find((item) => item.id === selectedId);
      if (match) return match;
    }
    for (const section of data.sections) {
      const match = section.items.find((item) => item.id === selectedId);
      if (match) return match;
    }
    return null;
  }, [data.sections, filteredSections, selectedId]);

  return (
    <main className="h-screen overflow-hidden overflow-x-hidden bg-[radial-gradient(circle_at_top,#EDF4FF_0%,#F5F8FD_45%,#EEF3FF_100%)] p-5 text-slate-900">
      <div className="relative mx-auto flex h-[calc(100vh-40px)] min-w-0 max-w-[1680px] flex-col overflow-hidden rounded-[32px] border border-white/70 bg-white/70 shadow-[0_28px_72px_rgba(148,163,184,0.18)] backdrop-blur-sm">
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
        <SessionsListTopBar teamName={data.teamName} teamMembersLabel={data.teamMembersLabel} userInitials={data.user.initials} />

        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
          <aside className="flex w-[176px] shrink-0 flex-col justify-between border-r border-slate-200/90 bg-[#f8fafc] px-3 py-4">
            <nav className="space-y-1.5">
              {(
                [
                  ["主页", "home", "/" as const],
                  ["会话", "chat", "/sessions" as const],
                  ["文档", "doc", "#" as const],
                  ["画布", "canvas", "#" as const],
                  ["Agents", "agents", "#" as const],
                  ["设置", "settings", "#" as const],
                ] as const
              ).map(([label, icon, href]) => {
                const active = label === "会话";
                const inner = (
                  <>
                    <NavIcon type={icon} active={active} />
                    <span className="flex-1 text-left text-[14px] font-medium">{label}</span>
                  </>
                );
                const className = cn(
                  "flex w-full items-center gap-2.5 rounded-[16px] px-3 py-2.5 transition",
                  active ? "bg-blue-50 text-blue-600 shadow-[inset_3px_0_0_#2563EB]" : "text-slate-700 hover:bg-slate-50",
                );
                return href === "#" ? (
                  <button key={label} type="button" className={className}>
                    {inner}
                  </button>
                ) : (
                  <Link key={label} href={href} className={className}>
                    {inner}
                  </Link>
                );
              })}
            </nav>

            <div className={cn(detailDesignTokens.card.panel, "px-2.5 py-2.5")}>
              <div className="flex items-center gap-2.5">
                <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-[13px] font-semibold text-slate-700">
                  {data.user.initials}
                  <span className="absolute bottom-0.5 right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-semibold text-slate-950">{data.user.name}</p>
                  <p className="mt-0.5 truncate text-[12px] text-slate-500">{data.user.email}</p>
                </div>
              </div>
            </div>
          </aside>

          <div className={cn("grid min-h-0 min-w-0 flex-1 grid-cols-1", selectedItem && isDetailOpen ? "xl:grid-cols-[minmax(0,1fr)_388px]" : "xl:grid-cols-1")}>
            <motion.div layout className={cn("flex min-h-0 min-w-0 flex-1 flex-col bg-white", selectedItem && isDetailOpen ? "border-r border-slate-200/90" : "")}>
              <div className="shrink-0 bg-white px-4 pb-2.5 pt-2.5">
                <div className="min-w-0 border-b border-slate-200/90 pb-2.5">
                  <h1 className="text-[17px] font-semibold leading-tight tracking-[-0.03em] text-slate-950">会话</h1>
                  <p className="mt-0.5 max-w-2xl text-[12px] leading-snug text-slate-500">
                    查看和管理从即时消息路由而来的不同会话，并进入聊天、文稿或画布输出。
                  </p>
                </div>
              </div>

              <div className="flex min-h-0 min-w-0 flex-1 flex-col">
                <div className="min-h-0 flex-1 space-y-2.5 overflow-y-auto px-3 py-2.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <div className="flex h-9 min-w-[160px] flex-1 items-center gap-2 rounded-[12px] border border-slate-200 bg-[#fafbfc] px-2.5">
                      <TopSearchIcon />
                      <span className="text-[12px] text-slate-400">搜索会话</span>
                    </div>
                    <button
                      type="button"
                      className="inline-flex h-9 items-center rounded-[12px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700"
                    >
                      筛选
                    </button>
                    <button type="button" className="inline-flex h-9 items-center gap-0.5 rounded-[12px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-700">
                      最新优先
                      <span className="text-slate-400">⌄</span>
                    </button>
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
                        当前筛选暂无会话，试试切换到“全部”。
                      </div>
                    ) : null}
                    {filteredSections.map((section) => (
                      <div key={section.title}>
                        <h3 className="pb-1.5 text-[12px] font-semibold uppercase tracking-wide text-slate-500">{section.title}</h3>
                        <div className="space-y-1.5">
                          {section.items.map((item) => {
                            const active = selectedItem?.id === item.id;
                            return (
                              <div
                                key={item.id}
                                role="button"
                                tabIndex={0}
                                onClick={() => selectSession(item.id)}
                                onKeyDown={(event) => {
                                  if (event.key === "Enter" || event.key === " ") {
                                    event.preventDefault();
                                    selectSession(item.id);
                                  }
                                }}
                                className={cn(
                                  "flex w-full items-start gap-2 rounded-[14px] border px-2.5 py-2 text-left transition",
                                  active
                                    ? "border-blue-300/90 bg-blue-50/80 shadow-[0_4px_14px_rgba(37,99,235,0.08)]"
                                    : "border-slate-200/90 bg-[#fafbfc] hover:border-slate-300 hover:bg-white",
                                )}
                              >
                                <ItemModeIcon kind={item.kind} compact />
                                <div className="grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-start gap-x-3 gap-y-1">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1">
                                      <h4 className="truncate text-[13px] font-semibold leading-tight text-slate-900">{item.title}</h4>
                                      <button
                                        type="button"
                                        onClick={(event) => {
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
                                    </div>
                                    <p className="mt-0.5 line-clamp-1 text-[11px] leading-snug text-slate-500">{item.summary}</p>
                                  </div>
                                  <div className="flex max-w-full flex-wrap items-center justify-center gap-1 self-start px-0.5 pt-0.5">
                                    <div className="flex items-center gap-0.5 text-[11px] text-slate-600">
                                      <SourceIcon source={item.source} compact />
                                      <span className="max-w-[4rem] truncate">{item.source}</span>
                                    </div>
                                    <KindPill kind={item.kind} kindLabel={item.kindLabel} className="!min-h-6 px-2 py-0.5 text-[10px]" />
                                    <StatusPill status={statusToWorkflow(getRuntimeStatus(item))}>
                                      <span className="text-[10px]">{getRuntimeStatus(item)}</span>
                                    </StatusPill>
                                  </div>
                                  <div className="flex flex-col items-end gap-1 justify-self-end pt-0.5">
                                    <span className="text-[11px] tabular-nums text-slate-400">{getRuntimeUpdatedAt(item)}</span>
                                    <AvatarStack participants={item.participants} compact />
                                  </div>
                                </div>
                              </div>
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
                  className="flex min-h-0 min-w-0 flex-col bg-white px-3 pb-3 pt-2.5 xl:pl-4 xl:pr-4"
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
                        <button type="button" className={cn(detailDesignTokens.button.control, "min-w-[120px] flex-1 justify-center sm:flex-none")}>
                          继续
                        </button>
                        <button type="button" className={cn(detailDesignTokens.button.control, "gap-1")}>
                          导出 <span className="text-slate-400">⌄</span>
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
                          {selectedItem.preview.collaborators.map((person) => (
                            <div
                              key={person.id}
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
      </div>
    </main>
  );
}
