import { cn } from "@/components/UiPrimitives";
import type { WorkflowStatus, WorkflowStep } from "@/types/workspace";

const lineColor = {
  completed: "bg-emerald-300/95",
  // Screenshot uses green line up to current step.
  running: "bg-emerald-300/95",
  pending: "bg-slate-200/95",
  warning: "bg-amber-200/95",
} as const;

function StepIcon({ icon, tone }: { icon: WorkflowStep["icon"]; tone: "emerald" | "blue" | "slate" }) {
  const stroke = tone === "emerald" ? "#22C55E" : tone === "blue" ? "#2563EB" : "#94A3B8";
  switch (icon) {
    case "chat":
      return (
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M5 6.6C5 5.72 5.72 5 6.6 5H13.4C14.28 5 15 5.72 15 6.6V12.1C15 12.98 14.28 13.7 13.4 13.7H8.2L5 15V6.6Z"
            stroke={stroke}
            strokeWidth="1.7"
            strokeLinejoin="round"
          />
          <path d="M7.2 8.1H12.8" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M7.2 10.6H11.2" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    case "intent":
      return (
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="6.5" stroke={stroke} strokeWidth="1.7" />
          <path d="M10 6.7V10.2L12.4 11.6" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M4.9 5.2L6.4 6.2" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
    case "search":
      return (
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="9" cy="9" r="5.5" stroke={stroke} strokeWidth="1.7" />
          <path d="M13.2 13.2L17 17" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
    case "star":
      return (
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M10 3.1l2.1 4.6 5 .7-3.7 3.5.9 4.9L10 14.9 5.7 16.8l.9-4.9L2.9 8.4l5-.7L10 3.1Z"
            fill={stroke}
            opacity="0.95"
          />
        </svg>
      );
    case "ppt":
      return (
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M6.2 4.4H12.2L14.8 7v9.1H6.2V4.4Z" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M12 4.6V7.2H14.6" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M7.6 9.2H12.9" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M7.6 12H11.8" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    case "sync":
      return (
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M10 4.2v7.9" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
          <path d="M7.2 9.7 10 12.4l2.8-2.7" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M5.4 15.8h9.2" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
    default:
      return (
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="2.2" fill={stroke} />
        </svg>
      );
  }
}

function StepStatusPill({ status }: { status: WorkflowStatus }) {
  const label = status === "completed" ? "已完成" : status === "running" ? "正在进行" : status === "warning" ? "预警" : "等待中";
  const cls =
    status === "completed"
      ? "text-emerald-600"
      : status === "running"
        ? "text-blue-600"
        : status === "warning"
          ? "text-amber-600"
          : "text-slate-400";
  return <span className={cn("mt-1 text-[9px] font-semibold leading-none", cls)}>{label}</span>;
}

function StepperNode({ step }: { step: WorkflowStep }) {
  if (step.status === "completed") {
    return (
      <span className="relative flex h-8 w-8 items-center justify-center rounded-full border border-emerald-200 bg-white shadow-[0_6px_14px_rgba(34,197,94,0.10)]">
        <StepIcon icon={step.icon} tone="emerald" />
        <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 shadow-[0_6px_14px_rgba(34,197,94,0.22)]">
          <svg width="10" height="10" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M3 7.2L5.7 9.9L11 4.6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </span>
    );
  }

  if (step.status === "running") {
    return (
      <span className="relative flex h-9 w-9 items-center justify-center">
        <span className="stepper-running-pulse absolute inset-0 rounded-full bg-blue-400/10" />
        <span className="absolute inset-[1px] rounded-full border border-blue-200/90 bg-white shadow-[0_8px_18px_rgba(59,130,246,0.10)]" />
        <span className="stepper-running-ring absolute inset-[4px] rounded-full border-[3px] border-blue-500 border-r-blue-100 border-b-blue-100 bg-blue-50/90 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.5)]" />
        <span className="absolute inset-[9px] flex items-center justify-center rounded-full bg-white">
          <StepIcon icon={step.icon ?? "star"} tone="blue" />
        </span>
      </span>
    );
  }

  if (step.status === "warning") {
    return (
      <span className="flex h-8 w-8 items-center justify-center rounded-full border border-amber-200 bg-amber-50 shadow-[0_6px_14px_rgba(245,158,11,0.14)]">
        <StepIcon icon={step.icon} tone="slate" />
      </span>
    );
  }

  return (
    <span className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-300 shadow-[0_6px_14px_rgba(148,163,184,0.10)]">
      <StepIcon icon={step.icon} tone="slate" />
    </span>
  );
}

export function Stepper({ steps, className }: { steps: WorkflowStep[]; className?: string }) {
  return (
    <div className={cn("mt-2 min-w-0", className)}>
      <div className="grid min-w-[520px] gap-1" style={{ gridTemplateColumns: `repeat(${Math.max(1, steps.length)}, minmax(0, 1fr))` }}>
        {steps.map((step, index) => (
          <div key={`${index}-${step.id}`} className="relative flex min-w-0 flex-col items-center text-center">
            {index < steps.length - 1 && (
              <div className="absolute left-[calc(50%+16px)] top-[14px] flex w-[calc(100%-32px)] items-center">
                <span className={`h-[2px] flex-1 rounded-full ${lineColor[step.status]} shadow-[0_1px_4px_rgba(148,163,184,0.12)]`} />
              </div>
            )}

            <div className="rounded-full bg-white/95 p-0.5 shadow-[0_6px_14px_rgba(148,163,184,0.12)] ring-1 ring-slate-100/80">
              <StepperNode step={step} />
            </div>
            <p className="mt-1 max-w-[96px] text-[10px] font-medium leading-[14px] text-slate-800">
              {step.id}. {step.title}
            </p>
            <StepStatusPill status={step.status} />
          </div>
        ))}
      </div>
    </div>
  );
}
