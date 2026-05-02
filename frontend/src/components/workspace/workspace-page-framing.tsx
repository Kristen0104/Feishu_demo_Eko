import type { ReactNode } from "react";

export function WorkspacePageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="shrink-0 border-b border-slate-200/90 bg-white px-7 pb-4 pt-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">{title}</h1>
          {description ? <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-slate-500">{description}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}
