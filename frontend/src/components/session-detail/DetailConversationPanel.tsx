import { SessionDetailData } from "@/types/session-detail";

import { MessageInput } from "@/components/MessageInput";
import { MoreIcon } from "@/components/Icons";

import { DetailConversationMessage } from "./DetailConversationMessage";

export function DetailConversationPanel({ data }: { data: SessionDetailData }) {
  const tone = data.layoutVariant === "canvas" ? "canvas" : data.layoutVariant === "doc" ? "doc" : "chat";
  return (
    <section className="flex h-full min-h-[820px] flex-col rounded-[30px] border border-slate-200/90 bg-white p-5 shadow-[0_18px_36px_rgba(148,163,184,0.08)]">
      <div className="flex items-center justify-between">
        <h2 className="text-[18px] font-semibold text-slate-950">{data.conversationTitle}</h2>
        <div className="flex items-center gap-2">
          <button className="rounded-full border border-transparent p-2 hover:bg-slate-50">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path d="M3.5 5.4L9 2.5L14.5 5.4V12.6L9 15.5L3.5 12.6V5.4Z" stroke="#475569" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
          </button>
          <button className="rounded-full border border-transparent p-2 hover:bg-slate-50">
            <MoreIcon />
          </button>
        </div>
      </div>

      <div className="mt-4 flex min-h-0 flex-1 border-t border-slate-100 pt-4">
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex-1 space-y-7 overflow-y-auto pr-1">
            {data.messages.map((message, mi) => (
              <DetailConversationMessage key={message.id ?? `m-${mi}`} message={message} tone={tone} />
            ))}
          </div>

          <div className="mt-5">
            <MessageInput tone={tone} placeholder="继续让 Eko 处理…" />
          </div>
        </div>
      </div>
    </section>
  );
}
