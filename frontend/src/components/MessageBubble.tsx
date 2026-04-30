import { MessageItem, ScenarioData } from "@/types/workspace";

import { ChatModeIcon } from "./Icons";
import { cn } from "./UiPrimitives";

const accentBackground = {
  chat: "border-emerald-200 bg-emerald-50/80",
  doc: "border-blue-200 bg-blue-50/80",
  canvas: "border-violet-200 bg-violet-50/80",
} as const;

export function MessageBubble({
  message,
  scenario,
}: {
  message: MessageItem;
  scenario: ScenarioData;
}) {
  const isEko = message.role === "eko";

  return (
    <div className="flex gap-3">
      <div className="pt-2">
        {isEko ? (
          <ChatModeIcon tone={scenario.accent} />
        ) : (
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-[16px] font-semibold text-slate-700 shadow-[inset_0_1px_1px_rgba(255,255,255,0.7)]">
            {message.avatar}
          </span>
        )}
      </div>

      <div
        className={cn(
          "min-h-[112px] min-w-0 flex-1 rounded-[22px] border px-5 py-4 shadow-[0_8px_20px_rgba(15,23,42,0.04)]",
          isEko ? accentBackground[scenario.accent] : "border-slate-200 bg-white",
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-semibold text-slate-950">{message.author}</span>
            {isEko && (
              <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold tracking-[0.12em] text-slate-400">
                应用
              </span>
            )}
          </div>
          <span className="shrink-0 pt-1 text-[12px] text-slate-400">{message.time}</span>
        </div>

        <div className="mt-3 space-y-2 text-[15px] leading-8 text-slate-700">
          {message.mention && (
            <span className="inline-flex rounded-xl border border-slate-200 bg-white px-2 py-1 text-[13px] font-semibold text-slate-600">
              {message.mention}
            </span>
          )}
          <p>{message.body}</p>
        </div>
      </div>
    </div>
  );
}
