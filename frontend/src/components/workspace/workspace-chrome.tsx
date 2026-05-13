"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";

import { EkoSquircleMark } from "@/components/login/brand-icons";
import { ChevronCollapseIcon } from "@/components/Icons";
import { detailDesignTokens } from "@/components/session-detail/designTokens";
import { cn } from "@/components/UiPrimitives";
import { fetchMySessionInvites, updateSessionInvite } from "@/lib/team-api";
import type { WorkspaceBreadcrumbSegment } from "@/lib/workspace-breadcrumb";
import type { WorkspaceNavKey } from "@/lib/workspace-nav";
import { useAppStore } from "@/store/app-store";
import type { SessionListPageData } from "@/types/session";
import type { SessionInvite } from "@/types/team";

import { SessionWorkspaceSearchProvider, useSessionWorkspaceSearch } from "@/components/workspace/session-workspace-search";

export type { WorkspaceNavKey };

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

function formatInviteExpiry(expiresAt: string): string {
  const expires = new Date(expiresAt).getTime();
  if (!Number.isFinite(expires)) return "24 小时内有效";
  const diffMs = expires - Date.now();
  if (diffMs <= 0) return "已过期";
  const hours = Math.ceil(diffMs / (60 * 60 * 1000));
  return hours >= 24 ? "24 小时内有效" : `${hours} 小时内有效`;
}

function SessionInviteToast() {
  const [invites, setInvites] = useState<SessionInvite[]>([]);
  const [visible, setVisible] = useState(false);
  const pendingInvites = useMemo(
    () => invites.filter((invite) => invite.status === "pending" && !invite.isExpired),
    [invites],
  );
  const firstInvite = pendingInvites[0];

  const loadInvites = async () => {
    try {
      const data = await fetchMySessionInvites();
      setInvites(data);
      if (data.some((invite) => invite.status === "pending" && !invite.isExpired)) {
        setVisible(true);
      }
    } catch {
      /* keep the workspace quiet if auth/session is not ready */
    }
  };

  useEffect(() => {
    const initialTimer = window.setTimeout(() => void loadInvites(), 0);
    const timer = window.setInterval(() => void loadInvites(), 15000);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(timer);
    };
  }, []);

  if (!visible || !firstInvite) return null;

  return (
    <div className="absolute right-5 top-[86px] z-50 hidden w-[330px] rounded-[18px] border border-slate-200 bg-white p-4 shadow-[0_22px_60px_rgba(15,23,42,0.18)] lg:block">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-blue-600">新的会话协作邀请</p>
          <h3 className="mt-1 line-clamp-2 text-[15px] font-semibold text-slate-950">{firstInvite.sessionTitle}</h3>
          <p className="mt-1 text-[12px] text-slate-500">
            {firstInvite.inviterName} 邀请你加入 · {formatInviteExpiry(firstInvite.expiresAt)}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setVisible(false)}
          className="rounded-full px-2 py-1 text-[14px] text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          aria-label="关闭邀请提示"
        >
          ×
        </button>
      </div>
      <div className="mt-4 flex items-center gap-2">
        <Link
          href={`/sessions/${encodeURIComponent(firstInvite.sessionId)}`}
          prefetch={false}
          onClick={() => {
            void updateSessionInvite(firstInvite.id, "accepted").then(loadInvites);
          }}
          className="rounded-[11px] bg-blue-600 px-3 py-2 text-[13px] font-semibold text-white"
        >
          加入会话
        </Link>
        <button
          type="button"
          onClick={() => {
            void updateSessionInvite(firstInvite.id, "dismissed").then(loadInvites);
            setVisible(false);
          }}
          className="rounded-[11px] border border-slate-200 bg-white px-3 py-2 text-[13px] font-semibold text-slate-600"
        >
          稍后
        </button>
        {pendingInvites.length > 1 ? (
          <span className="ml-auto text-[12px] text-slate-400">还有 {pendingInvites.length - 1} 条</span>
        ) : null}
      </div>
    </div>
  );
}

export function WorkspaceTopBar({
  teamName,
  teamMembersLabel,
  userInitials,
  breadcrumb,
}: {
  teamName: string;
  teamMembersLabel: string;
  userInitials: string;
  breadcrumb: WorkspaceBreadcrumbSegment[];
}) {
  const pathname = usePathname() ?? "";
  const isSessionDetail = /^\/sessions\/[^/]+$/.test(pathname);
  const { query: sessionSearchQuery, setQuery: setSessionSearchQuery } = useSessionWorkspaceSearch();
  const searchInputId = useId();
  const searchInputRef = useRef<HTMLInputElement>(null);
  const currentBreadcrumb = breadcrumb.find((segment) => segment.current) ?? breadcrumb[breadcrumb.length - 1];
  const mobileTitle = currentBreadcrumb?.label ?? "工作台";

  useEffect(() => {
    if (!isSessionDetail) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isSessionDetail]);

  return (
    <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200/90 px-3 lg:h-[72px] lg:px-6">
      <div className="flex min-w-0 items-center gap-2.5 lg:gap-5">
        <Link href="/home" prefetch={false} className="flex items-center gap-2.5 rounded-xl outline-none ring-offset-2 focus-visible:ring-2 focus-visible:ring-blue-500 lg:gap-3">
          <EkoSquircleMark className="h-12 w-12 rounded-[14px] shadow-[0_10px_28px_rgba(37,99,235,0.22)] lg:h-14 lg:w-14 lg:rounded-[16px]" />
          <span className="hidden text-[16px] font-semibold tracking-[-0.04em] text-slate-950 sm:inline">Eko</span>
        </Link>
        <span className="min-w-0 truncate text-[15px] font-semibold text-slate-800 lg:hidden">{mobileTitle}</span>
        <nav className="hidden min-w-0 items-center gap-1.5 text-[14px] xl:flex" aria-label="面包屑">
          {breadcrumb.map((segment, index) => (
            <span key={`${segment.label}-${index}`} className="flex min-w-0 items-center gap-1.5">
              {index > 0 ? <span className="shrink-0 text-slate-300">/</span> : null}
              {segment.href && !segment.current ? (
                <Link
                  href={segment.href}
                  prefetch={false}
                  className="min-w-0 truncate text-slate-500 transition hover:text-slate-800"
                >
                  {segment.label}
                </Link>
              ) : (
                <span
                  className={
                    segment.current
                      ? "min-w-0 truncate font-semibold text-slate-800"
                      : "min-w-0 truncate text-slate-500"
                  }
                >
                  {segment.label}
                </span>
              )}
            </span>
          ))}
        </nav>
      </div>
      <div className="flex min-w-0 flex-1 items-center justify-end gap-2 pl-2 lg:gap-3 lg:pl-3">
        {isSessionDetail ? (
          <label
            htmlFor={searchInputId}
            className="hidden h-10 min-w-0 max-w-[min(332px,42vw)] flex-1 cursor-text items-center gap-3 rounded-[15px] border border-slate-200 bg-white px-4 shadow-[0_4px_12px_rgba(15,23,42,0.03)] lg:flex"
          >
            <TopSearchIcon />
            <input
              ref={searchInputRef}
              id={searchInputId}
              type="search"
              value={sessionSearchQuery}
              onChange={(e) => setSessionSearchQuery(e.target.value)}
              placeholder="搜索对话与上下文（⌘K）"
              autoComplete="off"
              className="min-w-0 flex-1 bg-transparent text-[14px] text-slate-800 placeholder:text-slate-400 outline-none"
            />
          </label>
        ) : (
          <div className="hidden h-10 min-w-0 max-w-[min(332px,42vw)] flex-1 items-center gap-3 rounded-[15px] border border-slate-200 bg-white px-4 shadow-[0_4px_12px_rgba(15,23,42,0.03)] lg:flex">
            <TopSearchIcon />
            <span className="min-w-0 flex-1 truncate text-[14px] text-slate-400">搜索（⌘K）</span>
          </div>
        )}
        <Link
          href="/team"
          prefetch={false}
          className="hidden min-w-[170px] max-w-[220px] shrink-0 items-center justify-between gap-2 rounded-[16px] border border-slate-200 bg-white px-3 py-2.5 text-left shadow-[0_4px_12px_rgba(15,23,42,0.03)] xl:flex"
          aria-label="打开团队空间"
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
        </Link>
        <Link
          href="/settings"
          prefetch={false}
          className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.03)] lg:flex"
          aria-label="帮助"
        >
          <HelpIcon />
        </Link>
        <Link
          href="/profile/notifications"
          prefetch={false}
          className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.03)] lg:h-10 lg:w-10"
          aria-label="通知"
        >
          <BellIcon />
          <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold leading-none text-white">
            1
          </span>
        </Link>
        <Link
          href="/profile"
          prefetch={false}
          className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[13px] font-semibold text-slate-700 shadow-[0_4px_12px_rgba(15,23,42,0.03)] outline-none ring-offset-2 transition hover:bg-slate-200/90 hover:ring-2 hover:ring-blue-400/40 focus-visible:ring-2 focus-visible:ring-blue-500 lg:h-11 lg:w-11 lg:text-[14px]"
          aria-label="打开个人资料"
        >
          {userInitials}
          <span className="absolute bottom-0.5 right-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-500" />
        </Link>
      </div>
    </div>
  );
}

type NavIconType =
  | "home"
  | "chat"
  | "doc"
  | "knowledge"
  | "share"
  | "tasks"
  | "team"
  | "appsGrid"
  | "settings";

function NavIcon({ type, active }: { type: NavIconType; active?: boolean }) {
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
    case "knowledge":
      return (
        <svg {...common}>
          <path d="M4.2 4.2H9.5C10.9 4.2 12 5.3 12 6.7V16.2H6.7C5.3 16.2 4.2 15.1 4.2 13.7V4.2Z" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M7 7H9.8M7 9.8H9.6" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
          <path d="M12 5.2H13.2C14.6 5.2 15.8 6.4 15.8 7.8V15.2" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "share":
      return (
        <svg {...common}>
          <circle cx="6" cy="10" r="2.2" stroke={stroke} strokeWidth="1.5" />
          <circle cx="14" cy="6" r="2.2" stroke={stroke} strokeWidth="1.5" />
          <circle cx="14" cy="14" r="2.2" stroke={stroke} strokeWidth="1.5" />
          <path d="M7.7 9L12.3 6.8M7.7 11L12.3 13.2M12.3 6.8L12.3 13.2" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "tasks":
      return (
        <svg {...common}>
          <circle cx="10" cy="10" r="7" stroke={stroke} strokeWidth="1.5" />
          <path d="M6.8 10.2L9 12.4L13.2 7.8" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "team":
      return (
        <svg {...common}>
          <circle cx="7" cy="7.5" r="2.4" stroke={stroke} strokeWidth="1.5" />
          <circle cx="13" cy="7.5" r="2.4" stroke={stroke} strokeWidth="1.5" />
          <path d="M4 15.5C4.5 13.2 6.4 11.8 8.5 11.8H11.5C13.6 11.8 15.5 13.2 16 15.5" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "appsGrid":
      return (
        <svg {...common}>
          <rect x="3.2" y="3.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
          <rect x="11.2" y="3.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
          <rect x="3.2" y="11.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
          <rect x="11.2" y="11.2" width="5.6" height="5.6" rx="1.4" stroke={stroke} strokeWidth="1.5" />
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

const NAV_ROW: Array<{
  label: string;
  href: string;
  key: WorkspaceNavKey;
  icon: NavIconType;
}> = [
  { label: "主页", href: "/home", key: "home", icon: "home" },
  { label: "会话", href: "/sessions", key: "sessions", icon: "chat" },
  { label: "文档", href: "/documents", key: "documents", icon: "doc" },
  { label: "知识库", href: "/knowledge", key: "knowledge", icon: "knowledge" },
  { label: "分享 / 协作", href: "/share", key: "share", icon: "share" },
  { label: "任务", href: "/tasks", key: "tasks", icon: "tasks" },
  { label: "团队", href: "/team", key: "team", icon: "team" },
  { label: "应用", href: "/apps", key: "apps", icon: "appsGrid" },
  { label: "设置", href: "/settings", key: "settings", icon: "settings" },
];

const MOBILE_NAV_ROW = NAV_ROW.filter(({ key }) =>
  ["home", "sessions", "documents", "knowledge", "settings"].includes(key),
);

function MobileWorkspaceNav({ activeNav }: { activeNav: WorkspaceNavKey }) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 px-2 pb-[env(safe-area-inset-bottom)] pt-1 shadow-[0_-10px_30px_rgba(15,23,42,0.08)] backdrop-blur lg:hidden"
      aria-label="移动端主导航"
    >
      <div className="mx-auto grid h-[60px] max-w-[520px] grid-cols-5 items-center gap-1">
        {MOBILE_NAV_ROW.map(({ label, href, key, icon }) => {
          const active = activeNav === key;
          return (
            <Link
              key={key}
              href={href}
              prefetch={false}
              className={cn(
                "flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-[12px] px-1 py-1.5 text-[11px] font-medium transition-colors",
                active ? "bg-blue-50 text-blue-600" : "text-slate-500 active:bg-slate-100",
              )}
              aria-current={active ? "page" : undefined}
            >
              <NavIcon type={icon} active={active} />
              <span className="max-w-full truncate leading-tight">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

function WorkspaceSidebar({
  data,
  activeNav,
}: {
  data: Pick<SessionListPageData, "user">;
  activeNav: WorkspaceNavKey;
}) {
  const pathname = usePathname() ?? "";
  const sessionDetailChatOpen = useAppStore((s) => s.sessionDetailChatOpen);
  const toggleSessionDetailChatOpen = useAppStore((s) => s.toggleSessionDetailChatOpen);
  const isSessionDetailRoute = /^\/sessions\/[^/]+$/.test(pathname);

  return (
    <aside className="hidden w-[188px] shrink-0 flex-col justify-between border-r border-slate-200/90 bg-[#F8F9FA] px-3 py-4 lg:flex">
      <nav className="space-y-1" aria-label="主导航">
        {NAV_ROW.map(({ label, href, key, icon }) => {
          const active = activeNav === key;
          const className = cn(
            "flex w-full items-start gap-2.5 rounded-r-[14px] rounded-l-none px-2.5 py-2.5 transition-colors",
            active ? "bg-blue-50 text-blue-600 shadow-[inset_4px_0_0_0_#2563EB]" : "text-slate-600 hover:bg-white/90 hover:text-slate-900",
          );

          if (key === "sessions" && isSessionDetailRoute) {
            const sessionRowClass = cn(
              "flex w-full flex-row items-center gap-1 rounded-r-[14px] rounded-l-none px-2 py-2 transition-colors",
              active ? "bg-blue-50 text-blue-600 shadow-[inset_4px_0_0_0_#2563EB]" : "text-slate-600 hover:bg-white/90 hover:text-slate-900",
            );
            return (
              <div key={key} className={sessionRowClass}>
                <Link href={href} prefetch={false} className="flex min-w-0 flex-1 items-center gap-2.5 outline-none">
                  <NavIcon type={icon} active={active} />
                  <span className="min-w-0 flex-1 text-left text-[13px] font-medium leading-snug">{label}</span>
                </Link>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    toggleSessionDetailChatOpen();
                  }}
                  className="shrink-0 rounded-full border border-slate-200/90 bg-white p-1 text-slate-500 shadow-sm transition hover:bg-slate-50 hover:text-slate-700"
                  aria-label={sessionDetailChatOpen ? "收起对话区" : "展开对话区"}
                  title={sessionDetailChatOpen ? "收起对话区" : "展开对话区"}
                >
                  <ChevronCollapseIcon open={sessionDetailChatOpen} />
                </button>
              </div>
            );
          }

          const inner = (
            <>
              <NavIcon type={icon} active={active} />
              <span className="min-w-0 flex-1 text-left text-[13px] font-medium leading-snug">{label}</span>
            </>
          );
          return (
            <Link key={key} href={href} prefetch={false} className={className}>
              {inner}
            </Link>
          );
        })}
      </nav>

      <Link
        href="/profile"
        prefetch={false}
        className={cn(detailDesignTokens.card.panel, "block px-2.5 py-2.5 outline-none ring-offset-2 transition hover:bg-slate-50/90 focus-visible:ring-2 focus-visible:ring-blue-500")}
        aria-label="打开个人资料"
      >
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[13px] font-semibold text-slate-700">
            {data.user.initials}
            <span className="absolute bottom-0.5 right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[14px] font-semibold text-slate-950">{data.user.name}</p>
            <p className="mt-0.5 truncate text-[12px] text-slate-500">{data.user.email}</p>
          </div>
        </div>
      </Link>
    </aside>
  );
}

export function WorkspaceChrome({
  data,
  breadcrumb,
  activeNav,
  children,
}: {
  data: Pick<SessionListPageData, "teamName" | "teamMembersLabel" | "user">;
  breadcrumb: WorkspaceBreadcrumbSegment[];
  activeNav: WorkspaceNavKey;
  children: ReactNode;
}) {
  return (
    <SessionWorkspaceSearchProvider>
      <main className="h-dvh overflow-hidden overflow-x-hidden bg-[radial-gradient(circle_at_top,#EDF4FF_0%,#F5F8FD_45%,#EEF3FF_100%)] p-0 text-slate-900 lg:h-screen lg:p-5">
        <div className="relative mx-auto flex h-dvh min-w-0 flex-col overflow-hidden bg-white/70 lg:h-[calc(100vh-40px)] lg:max-w-[1680px] lg:rounded-[32px] lg:border lg:border-white/70 lg:shadow-[0_28px_72px_rgba(148,163,184,0.18)] lg:backdrop-blur-sm">
          <SessionInviteToast />
          <WorkspaceTopBar
            teamName={data.teamName}
            teamMembersLabel={data.teamMembersLabel}
            userInitials={data.user.initials}
            breadcrumb={breadcrumb}
          />

          <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden pb-[calc(68px+env(safe-area-inset-bottom))] lg:pb-0">
            <WorkspaceSidebar data={data} activeNav={activeNav} />
            {children}
          </div>
          <MobileWorkspaceNav activeNav={activeNav} />
        </div>
      </main>
    </SessionWorkspaceSearchProvider>
  );
}

export { TopSearchIcon };
