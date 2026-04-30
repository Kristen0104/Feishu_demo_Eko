import { DetailMessage } from "@/types/session-detail";
import { AccentTone } from "@/types/workspace";

import { ChatModeIcon } from "@/components/Icons";

export function DetailConversationMessage({
  message,
  tone = "doc",
  onActionButtonClick,
}: {
  message: DetailMessage;
  tone?: AccentTone;
  onActionButtonClick?: (label: string) => void;
}) {
  const isEko = message.role === "eko";
  const ekoBubbleClass =
    tone === "canvas"
      ? "border-violet-200 bg-gradient-to-br from-violet-50 to-fuchsia-50/80 shadow-[0_8px_16px_rgba(139,92,246,0.06)]"
      : tone === "chat"
        ? "border-emerald-200 bg-gradient-to-br from-emerald-50 to-lime-50/70 shadow-[0_8px_16px_rgba(34,197,94,0.05)]"
        : "border-blue-200 bg-gradient-to-br from-blue-50 to-blue-100/80 shadow-[0_8px_16px_rgba(59,130,246,0.05)]";

  const mentionClass =
    tone === "canvas"
      ? "text-violet-600"
      : tone === "chat"
        ? "text-emerald-600"
        : "text-blue-600";

  const helperClass =
    tone === "canvas"
      ? "text-violet-600 shadow-[0_4px_10px_rgba(139,92,246,0.06)]"
      : tone === "chat"
        ? "text-emerald-600 shadow-[0_4px_10px_rgba(34,197,94,0.05)]"
        : "text-blue-600 shadow-[0_4px_10px_rgba(59,130,246,0.05)]";

  return (
    <div className="flex gap-2">
      <div className="pt-0.5">
        {isEko ? (
          <ChatModeIcon tone={tone} />
        ) : (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-b from-slate-100 to-slate-200 text-[12px] font-semibold text-slate-700 shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)]">{message.avatar}</div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2"><span className="text-[14px] font-semibold text-slate-950">{message.author}</span><span className="text-[11px] text-slate-400">{message.time}</span></div>
        <div className={isEko ? `mt-1.5 ml-0.5 max-w-[232px] rounded-[18px] border px-3 py-2.5 ${ekoBubbleClass}` : "mt-1.5 ml-0.5 max-w-[236px] rounded-[18px] border border-slate-200 bg-slate-50/80 px-3 py-2.5 shadow-[0_6px_14px_rgba(15,23,42,0.03)]"}>
          {message.mention && <span className={`inline-flex rounded-xl bg-white px-2 py-1 text-[12px] font-semibold ${mentionClass} shadow-[0_3px_8px_rgba(15,23,42,0.05)]`}>{message.mention}</span>}
          <p className="mt-1.5 whitespace-pre-line break-words text-[13px] leading-[23px] text-slate-700">{message.body}</p>
          {message.helperText ? <div className={`mt-2.5 inline-flex max-w-full items-center gap-2 rounded-full bg-white/80 px-3 py-1.5 text-[12px] ${helperClass}`}><span className={`h-3 w-3 shrink-0 rounded-full border-2 ${tone === "canvas" ? "border-violet-500" : tone === "chat" ? "border-emerald-500" : "border-blue-500"} border-t-transparent animate-spin`} />{message.helperText}</div> : null}
          {message.fileCard ? <div className="mt-2.5 overflow-hidden rounded-[16px] border border-slate-200 bg-white px-3 py-2.5 shadow-[0_6px_16px_rgba(15,23,42,0.04)]"><div className="flex min-w-0 items-start justify-between gap-2.5"><div className="flex min-w-0 items-start gap-2.5"><div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[11px] border border-blue-200 bg-blue-50"><svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M5 3H11.7L15 6.3V17H5V3Z" stroke="#2563EB" strokeWidth="1.6" strokeLinejoin="round" /><path d="M11.5 3V6.5H15" stroke="#2563EB" strokeWidth="1.6" strokeLinejoin="round" /></svg></div><div className="min-w-0"><p className="truncate text-[13px] font-semibold text-slate-900">{message.fileCard.title}</p><p className="mt-1 text-[12px] font-medium text-blue-600">{message.fileCard.typeLabel}</p></div></div><span className="inline-flex shrink-0 whitespace-nowrap rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-600">{message.fileCard.statusLabel}</span></div></div> : null}
          {message.actionCard ? (
            <div className="mt-2.5 rounded-[16px] border border-violet-200 bg-white/85 px-3 py-3 shadow-[0_8px_18px_rgba(139,92,246,0.08)]">
              <p className="text-[13px] font-semibold text-slate-900">{message.actionCard.title}</p>
              {message.actionCard.description ? <p className="mt-1 text-[12px] leading-5 text-slate-500">{message.actionCard.description}</p> : null}
              <div className="mt-3 flex flex-wrap gap-2">
                {message.actionCard.buttons.map((button) => {
                  const buttonClass =
                    button.tone === "primary"
                      ? "border-blue-200 bg-blue-50 text-blue-600"
                      : button.tone === "success"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-600"
                        : "border-slate-200 bg-white text-slate-600";

                  return (
                    <button
                      key={button.label}
                      type="button"
                      onClick={() => onActionButtonClick?.(button.label)}
                      className={`inline-flex h-8 items-center whitespace-nowrap rounded-full border px-3 text-[12px] font-semibold shadow-[0_4px_10px_rgba(15,23,42,0.04)] transition hover:brightness-[0.98] ${buttonClass}`}
                    >
                      {button.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>
        {message.sent && <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />已发送 · {message.time}</div>}
      </div>
    </div>
  );
}
