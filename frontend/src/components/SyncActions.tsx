import { SyncActionItem } from "@/types/workspace";

import { StatusPill } from "./UiPrimitives";

export function SyncActions({ items }: { items: SyncActionItem[] }) {
  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div key={item.id} className="rounded-[18px] border border-slate-200 bg-white px-4 py-3.5">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[15px] font-semibold text-slate-950">{item.title}</p>
            <StatusPill status={item.status} />
          </div>
        </div>
      ))}
    </div>
  );
}
