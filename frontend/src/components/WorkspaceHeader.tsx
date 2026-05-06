import { HeaderBadge as HeaderBadgeType } from "@/types/workspace";

import { HeaderBadge } from "./UiPrimitives";

export function WorkspaceHeader({
  title,
  subtitle,
  badges,
}: {
  title: string;
  subtitle: string;
  badges: HeaderBadgeType[];
}) {
  return (
    <header className="rounded-[28px] border border-slate-200/90 bg-white/95 px-7 py-6 shadow-[0_12px_32px_rgba(148,163,184,0.12)]">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-[28px] font-semibold tracking-[-0.05em] text-slate-950 md:text-[30px]">
            {title}
          </h1>
          <p className="mt-2 text-[14px] text-slate-500">{subtitle}</p>
        </div>

        <div className="flex flex-wrap gap-3">
          {badges.map((badge) => (
            <HeaderBadge key={badge.label} tone={badge.tone}>
              {badge.label}
            </HeaderBadge>
          ))}
        </div>
      </div>
    </header>
  );
}
