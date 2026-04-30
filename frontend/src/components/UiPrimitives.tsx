import { ReactNode } from "react";

import { AccentTone, EvidenceTone, HeaderBadgeTone, WorkflowStatus } from "@/types/workspace";

export function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

const accentStyles: Record<AccentTone, { soft: string; strong: string; text: string; ring: string }> = {
  chat: {
    soft: "bg-emerald-50",
    strong: "bg-emerald-500",
    text: "text-emerald-600",
    ring: "border-emerald-200",
  },
  doc: {
    soft: "bg-blue-50",
    strong: "bg-blue-500",
    text: "text-blue-600",
    ring: "border-blue-200",
  },
  canvas: {
    soft: "bg-violet-50",
    strong: "bg-violet-500",
    text: "text-violet-600",
    ring: "border-violet-200",
  },
};

const headerBadgeStyles: Record<HeaderBadgeTone, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-600",
  info: "border-blue-200 bg-blue-50 text-blue-600",
  neutral: "border-slate-200 bg-white text-slate-500",
};

const workflowStyles: Record<WorkflowStatus, string> = {
  completed: "border-emerald-200 bg-emerald-50 text-emerald-600",
  running: "border-blue-200 bg-blue-50 text-blue-600",
  pending: "border-slate-200 bg-slate-50 text-slate-500",
  warning: "border-amber-200 bg-amber-50 text-amber-600",
};

const workflowLabels: Record<WorkflowStatus, string> = {
  completed: "已完成",
  running: "进行中",
  pending: "待处理",
  warning: "预警",
};

const evidenceStyles: Record<EvidenceTone, string> = {
  chat: "border-emerald-200 bg-emerald-50 text-emerald-600",
  document: "border-blue-200 bg-blue-50 text-blue-600",
  record: "border-violet-200 bg-violet-50 text-violet-600",
};

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-[26px] border border-slate-200/90 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.04)]",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function PanelTitle({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{eyebrow}</p>
        <h2 className="mt-2 text-[16px] font-semibold text-slate-950">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function AccentPill({
  tone,
  children,
  className,
}: {
  tone: AccentTone;
  children: ReactNode;
  className?: string;
}) {
  const style = accentStyles[tone];

  return (
    <span
      className={cn(
        "inline-flex min-h-8 shrink-0 items-center whitespace-nowrap rounded-full border px-3.5 py-1 text-[12px] font-semibold leading-none",
        style.soft,
        style.ring,
        style.text,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function HeaderBadge({
  tone,
  children,
}: {
  tone: HeaderBadgeTone;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex min-h-9 shrink-0 items-center whitespace-nowrap rounded-full border px-4 py-2 text-[12px] font-semibold leading-none",
        headerBadgeStyles[tone],
      )}
    >
      {children}
    </span>
  );
}

export function StatusPill({
  status,
  children,
}: {
  status: WorkflowStatus;
  children?: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex min-h-8 shrink-0 items-center whitespace-nowrap rounded-full border px-3.5 py-1 text-[12px] font-semibold leading-none",
        workflowStyles[status],
      )}
    >
      {children ?? workflowLabels[status]}
    </span>
  );
}

export function EvidencePill({
  tone,
  children,
}: {
  tone: EvidenceTone;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex min-h-8 shrink-0 items-center whitespace-nowrap rounded-full border px-3.5 py-1 text-[12px] font-semibold leading-none",
        evidenceStyles[tone],
      )}
    >
      {children}
    </span>
  );
}

export function metricCard(label: string, value: string) {
  return (
    <div className="min-w-[118px] rounded-[18px] border border-slate-200 bg-white px-4 py-3 shadow-[0_4px_12px_rgba(15,23,42,0.03)]">
      <p className="text-[12px] text-slate-400">{label}</p>
      <p className="mt-2 text-[20px] font-semibold tracking-[-0.04em] text-slate-950">{value}</p>
    </div>
  );
}

export function accentClasses(tone: AccentTone) {
  return accentStyles[tone];
}
