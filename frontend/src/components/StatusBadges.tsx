import { HeaderBadge as HeaderBadgeType } from "@/types/workspace";

import { HeaderBadge } from "./UiPrimitives";

export function StatusBadges({ items }: { items: HeaderBadgeType[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <HeaderBadge key={item.label} tone={item.tone}>
          {item.label}
        </HeaderBadge>
      ))}
    </div>
  );
}
