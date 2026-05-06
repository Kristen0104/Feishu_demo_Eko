import { ChatModeIcon } from "@/components/Icons";
import { ScenarioData } from "@/types/workspace";

const textColors = {
  chat: "text-emerald-500",
  doc: "text-blue-500",
  canvas: "text-violet-500",
} as const;

const lineColors = {
  chat: "border-emerald-300",
  doc: "border-blue-300",
  canvas: "border-violet-300",
} as const;

const dotColors = {
  chat: "bg-emerald-500",
  doc: "bg-blue-500",
  canvas: "bg-violet-500",
} as const;

export function SideRail({ scenario }: { scenario: ScenarioData }) {
  return (
    <aside className="flex w-[96px] flex-col items-center rounded-[30px] border border-slate-200/80 bg-white/90 px-3 py-7 shadow-[0_12px_32px_rgba(148,163,184,0.12)]">
      <ChatModeIcon tone={scenario.accent} />

      <div className="mt-8 text-center">
        <p className="text-[13px] text-slate-400">{scenario.railTitle}</p>
        <p className={`mt-2 text-[17px] font-semibold ${textColors[scenario.accent]}`}>{scenario.railSubtitle}</p>
        <p className="mt-2 text-[13px] leading-5 text-slate-500">{scenario.railCaption}</p>
      </div>

      <div className="mt-10 flex flex-1 flex-col items-center">
        <div className={`h-[280px] border-l border-dashed ${lineColors[scenario.accent]}`} />
        <span className={`mt-2 h-3 w-3 rounded-full ${dotColors[scenario.accent]}`} />
      </div>
    </aside>
  );
}
