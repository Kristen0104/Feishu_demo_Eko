import { ScenarioData } from "@/types/workspace";

import { ChatModeIcon } from "./Icons";

const accentBox = {
  chat: "border-emerald-200 bg-emerald-50/80",
  doc: "border-blue-200 bg-blue-50/80",
  canvas: "border-violet-200 bg-violet-50/80",
} as const;

export function ChatReplySurface({ scenario }: { scenario: ScenarioData }) {
  if (scenario.output.kind !== "chat") return null;

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-[18px] font-semibold text-slate-950">{scenario.output.title}</h3>
        <p className="mt-2 text-[13px] text-slate-500">{scenario.output.description}</p>
      </div>

      <div className={`rounded-[22px] border px-5 py-5 shadow-[0_8px_24px_rgba(15,23,42,0.03)] ${accentBox[scenario.accent]}`}>
        <div className="flex items-center gap-3">
          <ChatModeIcon tone={scenario.accent} />
          <div>
            <p className="text-[16px] font-semibold text-slate-950">Eko</p>
            <p className="mt-2 text-[15px] leading-8 text-slate-700">{scenario.output.reply}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {scenario.output.placeholders.map((item) => (
          <div
            key={item.title}
            className="rounded-[20px] border border-slate-200 bg-slate-50/70 px-5 py-5 text-slate-400"
          >
            <p className="text-[15px] font-semibold text-slate-500">{item.title}</p>
            <p className="mt-2 text-[12px]">{item.subtitle}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
