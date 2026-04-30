import { ScenarioData } from "@/types/workspace";

import { Stepper } from "./Stepper";
import { AccentPill, Card, metricCard } from "./UiPrimitives";

const legend = [
  { label: "已完成", color: "bg-emerald-500" },
  { label: "进行中", color: "bg-blue-500" },
  { label: "待处理", color: "bg-slate-300" },
  { label: "预警", color: "bg-amber-500" },
];

export function MissionControl({ scenario }: { scenario: ScenarioData }) {
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between gap-5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
              智能体任务控制
            </p>
            <AccentPill tone={scenario.accent}>{scenario.intentBadge}</AccentPill>
          </div>

          <h2 className="mt-5 text-[18px] font-semibold text-slate-950">
            {scenario.missionTitle}
          </h2>
          <p className="mt-3 max-w-[720px] text-[14px] leading-7 text-slate-500">
            {scenario.missionDescription}
          </p>
        </div>

        <div className="grid shrink-0 gap-3 sm:grid-cols-2">
          {metricCard("置信度", scenario.confidence)}
          {metricCard("上下文质量", scenario.contextQuality)}
        </div>
      </div>

      <Stepper steps={scenario.workflow} />

      <div className="mt-8 flex flex-wrap gap-x-8 gap-y-3">
        {legend.map((item) => (
          <div key={item.label} className="flex items-center gap-2 text-[13px] text-slate-500">
            <span className={`h-3 w-3 rounded-full ${item.color}`} />
            {item.label}
          </div>
        ))}
      </div>
    </Card>
  );
}
