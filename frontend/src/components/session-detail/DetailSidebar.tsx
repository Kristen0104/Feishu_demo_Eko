import { SessionDetailData } from "@/types/session-detail";

import { ChevronCollapseIcon } from "@/components/Icons";
import { cn } from "@/components/UiPrimitives";
import { detailDesignTokens } from "./designTokens";

function NavIcon({ type, active }: { type: SessionDetailData["navItems"][number]["icon"]; active?: boolean }) {
  const stroke = active ? "#2563EB" : "#475569";

  const common = {
    width: 20,
    height: 20,
    viewBox: "0 0 20 20",
    fill: "none",
    "aria-hidden": true,
  };

  switch (type) {
    case "home":
      return (
        <svg {...common}>
          <path d="M3 8.5L10 3L17 8.5V16.2H12.5V11.2H7.5V16.2H3V8.5Z" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      );
    case "chat":
      return (
        <svg {...common}>
          <rect x="3" y="3.5" width="14" height="10.5" rx="3" stroke={stroke} strokeWidth="1.6" />
          <path d="M7 14L6.3 17L9.5 14" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "doc":
      return (
        <svg {...common}>
          <path d="M6 2.8H12.2L15.8 6.4V17.2H6V2.8Z" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" />
          <path d="M12 2.8V6.6H15.8" stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      );
    case "share":
      return (
        <svg {...common}>
          <circle cx="5" cy="10" r="2.2" stroke={stroke} strokeWidth="1.6" />
          <circle cx="15" cy="5" r="2.2" stroke={stroke} strokeWidth="1.6" />
          <circle cx="15" cy="15" r="2.2" stroke={stroke} strokeWidth="1.6" />
          <path d="M7 9L13 6" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M7 11L13 14" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    case "task":
      return (
        <svg {...common}>
          <circle cx="10" cy="10" r="7" stroke={stroke} strokeWidth="1.6" />
          <path d="M7 10.2L9.1 12.3L13.4 8" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "team":
      return (
        <svg {...common}>
          <circle cx="7" cy="7.2" r="2.2" stroke={stroke} strokeWidth="1.6" />
          <circle cx="13.3" cy="8" r="1.9" stroke={stroke} strokeWidth="1.6" />
          <path d="M3.8 15.4C4.4 12.9 6.1 11.7 7.9 11.7C9.7 11.7 11.4 12.9 12 15.4" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M11.5 14.8C11.9 13.3 13 12.4 14.4 12.4C15.3 12.4 16.2 12.8 16.9 13.8" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    case "apps":
      return (
        <svg {...common}>
          <rect x="3.5" y="3.5" width="5.2" height="5.2" rx="1.2" stroke={stroke} strokeWidth="1.5" />
          <rect x="11.3" y="3.5" width="5.2" height="5.2" rx="1.2" stroke={stroke} strokeWidth="1.5" />
          <rect x="3.5" y="11.3" width="5.2" height="5.2" rx="1.2" stroke={stroke} strokeWidth="1.5" />
          <rect x="11.3" y="11.3" width="5.2" height="5.2" rx="1.2" stroke={stroke} strokeWidth="1.5" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <circle cx="10" cy="10" r="6.5" stroke={stroke} strokeWidth="1.6" />
          <path d="M10 6.8V13.2" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
          <path d="M6.8 10H13.2" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
  }
}

export function DetailSidebar({
  data,
  conversationOpen,
  onToggleConversation,
}: {
  data: SessionDetailData;
  conversationOpen: boolean;
  onToggleConversation: () => void;
}) {
  return (
    <aside className="flex w-[176px] shrink-0 flex-col justify-between border-r border-slate-200/90 px-3 py-5">
      <nav className="space-y-1.5">
        {data.navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={item.id === "chat" ? onToggleConversation : undefined}
            className={cn(
              "flex w-full items-center gap-3 rounded-[18px] px-4 py-3 text-left text-[15px] font-medium transition",
              item.active
                ? "bg-blue-50 text-blue-600 shadow-[inset_3px_0_0_#2563EB]"
                : "text-slate-700 hover:bg-slate-50",
            )}
          >
            <NavIcon type={item.icon} active={item.active} />
            <span className="flex-1">{item.label}</span>
            {item.id === "chat" ? (
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/90 shadow-[0_2px_6px_rgba(37,99,235,0.08)]">
                <ChevronCollapseIcon open={conversationOpen} />
              </span>
            ) : null}
          </button>
        ))}
      </nav>

      <div className={`${detailDesignTokens.card.panel} px-3 py-3`}>
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-[13px] font-semibold text-slate-700">
            SC
            <span className="absolute bottom-0.5 right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
          </div>
          <div className="min-w-0">
            <p className="max-w-[80px] break-words text-[14px] font-semibold leading-[18px] text-slate-950">{data.assistantName}</p>
            <p className="mt-0.5 text-[12px] text-slate-500">{data.assistantEmail}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
