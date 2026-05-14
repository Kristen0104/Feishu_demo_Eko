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
    <div className="shrink-0 border-b border-slate-200/90 bg-white px-3 pb-3 pt-4 sm:px-5 lg:px-7 lg:pb-4 lg:pt-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">{title}</h1>
          {description ? <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-slate-500">{description}</p> : null}
        </div>
        {actions ? <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:shrink-0">{actions}</div> : null}
      </div>
    </div>
  );
}
