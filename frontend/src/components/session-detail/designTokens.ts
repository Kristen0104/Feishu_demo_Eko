export const detailDesignTokens = {
  typography: {
    sectionTitle: "text-[20px] font-semibold tracking-[-0.03em]",
    cardTitle: "text-[17px] font-semibold",
    body: "text-[13px] leading-6",
    caption: "text-[12px] text-slate-500",
  },
  button: {
    control:
      "inline-flex h-10 items-center gap-2 rounded-[14px] border border-slate-200 bg-white px-4 text-[14px] font-semibold text-slate-700 shadow-[0_4px_12px_rgba(15,23,42,0.04)]",
    iconOnly:
      "flex h-10 w-10 items-center justify-center rounded-[14px] border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.04)]",
    primary:
      "inline-flex h-10 items-center gap-2 rounded-[14px] bg-blue-600 px-4 text-[14px] font-semibold text-white shadow-[0_10px_20px_rgba(37,99,235,0.2)]",
  },
  card: {
    pageFrame: "rounded-[20px] border border-slate-200/90 bg-white shadow-[0_12px_24px_rgba(148,163,184,0.08)]",
    content: "rounded-[18px] border border-slate-200 bg-white shadow-[0_6px_18px_rgba(15,23,42,0.03)]",
    panel: "rounded-[22px] border border-slate-200/90 bg-white shadow-[0_12px_24px_rgba(148,163,184,0.06)]",
  },
  spacing: {
    sectionPadding: "px-4 py-3",
    panelPadding: "px-[18px] py-3",
    compactGap: "gap-3",
  },
} as const;

