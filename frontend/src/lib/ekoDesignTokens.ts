/**
 * Eko Workspace 全局设计 token（登录、会话列表、会话详情共用基础语义）
 * 与 session-detail/designTokens 互补，用于跨页面一致留白与圆角层级。
 */
export const ekoRadius = {
  cardLg: "rounded-[28px]",
  cardMd: "rounded-[20px]",
  cardSm: "rounded-[16px]",
  input: "rounded-[12px]",
  pill: "rounded-full",
} as const;

export const ekoSurface = {
  pageBg:
    "bg-[radial-gradient(120%_80%_at_50%_0%,#EFF6FF_0%,#F1F5F9_45%,#F8FAFC_100%)]",
  card: "bg-white/95 border border-slate-200/90 shadow-[0_24px_64px_rgba(148,163,184,0.12)] backdrop-blur-sm",
  cardSubtle: "bg-white/90 border border-slate-200/80 shadow-[0_8px_28px_rgba(148,163,184,0.08)]",
} as const;

export const ekoSemantic = {
  chat: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  doc: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  canvas: { bg: "bg-violet-50", text: "text-violet-700", border: "border-violet-200" },
  synced: { bg: "bg-emerald-50/80", text: "text-emerald-700" },
  running: { bg: "bg-sky-50/90", text: "text-sky-700" },
  draft: { bg: "bg-slate-100", text: "text-slate-600" },
  pending: { bg: "bg-slate-100", text: "text-slate-600" },
  warning: { bg: "bg-amber-50", text: "text-amber-800" },
} as const;

export const ekoType = {
  display: "text-[28px] font-semibold tracking-[-0.04em] text-slate-900 sm:text-[32px]",
  title: "text-lg font-semibold text-slate-900",
  body: "text-[15px] leading-7 text-slate-600",
  caption: "text-[13px] text-slate-500",
  label: "text-xs font-medium uppercase tracking-[0.12em] text-slate-500",
} as const;

export const ekoButton = {
  primary:
    "inline-flex h-12 w-full items-center justify-center rounded-[14px] bg-gradient-to-b from-blue-500 to-blue-600 px-5 text-[15px] font-semibold text-white shadow-[0_8px_24px_rgba(37,99,235,0.25)] transition hover:brightness-[1.03] active:scale-[0.99]",
  oauth:
    "inline-flex h-11 w-full items-center justify-center gap-2 rounded-[14px] border border-slate-200/90 bg-white px-4 text-[14px] font-medium text-slate-700 shadow-[0_2px_8px_rgba(15,23,42,0.04)] transition hover:bg-slate-50/90",
} as const;
