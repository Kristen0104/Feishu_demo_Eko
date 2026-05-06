import type { ReactNode } from "react";

import { AccentTone, WorkflowStatus } from "@/types/workspace";

function iconWrap(children: ReactNode, className?: string) {
  return (
    <span
      className={[
        "inline-flex items-center justify-center",
        className ?? "",
      ].join(" ")}
    >
      {children}
    </span>
  );
}

export function ChatModeIcon({ tone }: { tone: AccentTone }) {
  const fills = {
    chat: "#22C55E",
    doc: "#3B82F6",
    canvas: "#8B5CF6",
  } as const;

  return iconWrap(
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <rect x="1" y="1" width="26" height="26" rx="8" fill={fills[tone]} />
      <path
        d="M8 18.4V9.8C8 8.806 8.806 8 9.8 8H18.2C19.194 8 20 8.806 20 9.8V15.2C20 16.194 19.194 17 18.2 17H11.7L8 18.4Z"
        stroke="white"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>,
  );
}

export function MoreIcon() {
  return iconWrap(
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="3" cy="8" r="1.1" fill="#94A3B8" />
      <circle cx="8" cy="8" r="1.1" fill="#94A3B8" />
      <circle cx="13" cy="8" r="1.1" fill="#94A3B8" />
    </svg>,
  );
}

export function ChevronCollapseIcon({ open }: { open: boolean }) {
  return iconWrap(
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path
        d={open ? "M8.75 3.5L5.25 7L8.75 10.5" : "M5.25 3.5L8.75 7L5.25 10.5"}
        stroke="#2563EB"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>,
  );
}

export function FeishuLeafIcon() {
  return iconWrap(
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M2.3 8.2C2.3 4.9 4.9 2.3 8.2 2.3H10.2L8.7 7H2.3V8.2Z" fill="#2F7CFF" />
      <path d="M13.6 7.7C13.6 11 11 13.6 7.7 13.6H5.7L7.2 8.9H13.6V7.7Z" fill="#2CCB72" />
    </svg>,
  );
}

export function ChatBadgeIcon() {
  return iconWrap(
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2.3" y="2.8" width="11.4" height="8.4" rx="2.6" stroke="#22C55E" strokeWidth="1.5" />
      <path d="M5.2 11.2L4.7 13.4L7.1 11.2" stroke="#22C55E" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>,
  );
}

export function StatusLoopIcon() {
  return iconWrap(
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M5 4.4H11.2V2.5L13.7 5L11.2 7.5V5.6H5C3.9 5.6 3 6.5 3 7.6" stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M11 11.6H4.8V13.5L2.3 11L4.8 8.5V10.4H11C12.1 10.4 13 9.5 13 8.4" stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>,
  );
}

export function PanelDocIcon({ tone = "blue" }: { tone?: "blue" | "gray" }) {
  const color = tone === "blue" ? "#2563EB" : "#475569";
  return iconWrap(
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M4.5 2.7H10.5L13.5 5.7V15.3H4.5V2.7Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M10.3 2.7V5.9H13.5" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>,
  );
}

export function ClockArrowIcon({ tone = "blue" }: { tone?: "blue" | "orange" }) {
  const color = tone === "orange" ? "#F59E0B" : "#2563EB";
  return iconWrap(
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <circle cx="9" cy="9" r="6" stroke={color} strokeWidth="1.5" />
      <path d="M9 5.8V9L11.1 10.2" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>,
  );
}

export function FeishuSendIcon() {
  return iconWrap(
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M3 5.5L9.2 3L15 5.8L9.6 8.2L3 5.5Z" fill="#2F7CFF" />
      <path d="M3.4 6.4L9.1 9.2L14.7 6.8V12.1L9.1 15L3.4 12.1V6.4Z" fill="#2CCB72" />
    </svg>,
  );
}

export function SendIcon({ tone }: { tone: AccentTone }) {
  const fills = {
    chat: "#22C55E",
    doc: "#3B82F6",
    canvas: "#8B5CF6",
  } as const;
  return iconWrap(
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path
        d="M15.75 2.25L2.625 8.4375L8.25 9.75L9.5625 15.375L15.75 2.25Z"
        stroke={fills[tone]}
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>,
  );
}

export function EmojiIcon() {
  return iconWrap(
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <circle cx="9" cy="9" r="6.3" stroke="#64748B" strokeWidth="1.4" />
      <circle cx="6.7" cy="7.3" r="0.8" fill="#64748B" />
      <circle cx="11.3" cy="7.3" r="0.8" fill="#64748B" />
      <path d="M6.2 10.6C6.95 11.55 7.9 12 9 12C10.1 12 11.05 11.55 11.8 10.6" stroke="#64748B" strokeWidth="1.4" strokeLinecap="round" />
    </svg>,
  );
}

export function ClipIcon() {
  return iconWrap(
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M6.4 9.4L10.8 5C11.78 4.02 13.36 4.02 14.34 5C15.32 5.98 15.32 7.56 14.34 8.54L8.7 14.18C7.33 15.55 5.12 15.55 3.75 14.18C2.38 12.81 2.38 10.6 3.75 9.23L9.09 3.89" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>,
  );
}

export function AtIcon() {
  return iconWrap(
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <circle cx="9" cy="9" r="6.6" stroke="#64748B" strokeWidth="1.4" />
      <path d="M11.9 9V7.8C11.9 6.47 10.82 5.4 9.5 5.4C8.18 5.4 7.1 6.47 7.1 7.8V9.2C7.1 10.52 8.18 11.6 9.5 11.6C10.82 11.6 11.9 10.52 11.9 9.2V9Z" stroke="#64748B" strokeWidth="1.4" />
      <path d="M11.9 10.2C12.18 10.6 12.64 10.9 13.2 10.9C14.14 10.9 14.9 10.14 14.9 9.2C14.9 5.94 12.26 3.3 9 3.3C5.74 3.3 3.1 5.94 3.1 9.2C3.1 12.46 5.74 15.1 9 15.1" stroke="#64748B" strokeWidth="1.3" strokeLinecap="round" />
    </svg>,
  );
}

export function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M3 7.2L5.7 9.9L11 4.6" stroke="white" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function DotIcon() {
  return <span className="h-2.5 w-2.5 rounded-full bg-current" />;
}

export function WarningIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M7 1.8L12 11.3H2L7 1.8Z" fill="#F59E0B" />
      <path d="M7 5V7.8" stroke="white" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="7" cy="9.8" r="0.8" fill="white" />
    </svg>
  );
}

export function WorkflowStatusIcon({ status }: { status: WorkflowStatus }) {
  if (status === "completed") {
    return (
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 shadow-[0_8px_18px_rgba(34,197,94,0.25)]">
        <CheckIcon />
      </span>
    );
  }

  if (status === "running") {
    return (
      <span className="relative flex h-9 w-9 items-center justify-center">
        <span className="stepper-running-pulse absolute inset-0 rounded-full bg-blue-400/10" />
        <span className="absolute inset-[1px] rounded-full border border-blue-200/90 bg-white shadow-[0_8px_18px_rgba(59,130,246,0.1)]" />
        <span className="stepper-running-ring absolute inset-[4px] rounded-full border-[3px] border-blue-500 border-r-blue-100 border-b-blue-100 bg-blue-50/90 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.5)]" />
        <span className="absolute inset-[11px] rounded-full bg-blue-500 shadow-[0_0_0_3px_rgba(59,130,246,0.08)]" />
      </span>
    );
  }

  if (status === "warning") {
    return (
      <span className="flex h-8 w-8 items-center justify-center rounded-full border border-amber-200 bg-amber-50 shadow-[0_8px_18px_rgba(245,158,11,0.16)]">
        <WarningIcon />
      </span>
    );
  }

  return (
    <span className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-400 shadow-[0_6px_14px_rgba(148,163,184,0.12)]">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
    </span>
  );
}

export function NodeGlyph({ type }: { type: "trend" | "rocket" | "calendar" | "spark" | "alert" | "check" }) {
  const styles = {
    trend: "text-violet-500",
    rocket: "text-blue-500",
    calendar: "text-emerald-500",
    spark: "text-amber-500",
    alert: "text-rose-500",
    check: "text-violet-500",
  } as const;

  const glyph = {
    trend: "↗",
    rocket: "✦",
    calendar: "✓",
    spark: "✷",
    alert: "!",
    check: "◌",
  } as const;

  return <span className={`text-[18px] font-semibold ${styles[type]}`}>{glyph[type]}</span>;
}
