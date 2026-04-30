import { ContextItem } from "@/types/workspace";

import { StatusPill } from "./UiPrimitives";

export function ContextSources({ items }: { items: ContextItem[] }) {
  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div key={item.id} className="rounded-[18px] border border-slate-200 bg-white px-4 py-3.5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[15px] font-semibold text-slate-950">{item.title}</p>
              <p className="mt-1.5 text-[12px] leading-6 text-slate-500">{item.description}</p>
            </div>
            <div className="pt-0.5">
              <StatusPill status={item.status} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
