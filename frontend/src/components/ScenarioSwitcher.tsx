import { ScenarioKey, WorkspaceData } from "@/types/workspace";

import { cn } from "./UiPrimitives";

const buttonStyles = {
  chat: {
    active: "border-emerald-300 bg-emerald-50 text-emerald-600",
    idle: "border-slate-200 bg-white text-slate-700 hover:border-emerald-200 hover:bg-emerald-50/50",
  },
  doc: {
    active: "border-blue-300 bg-blue-500 text-white shadow-[0_10px_20px_rgba(59,130,246,0.18)]",
    idle: "border-slate-200 bg-white text-slate-700 hover:border-blue-200 hover:bg-blue-50/50",
  },
  canvas: {
    active: "border-violet-300 bg-violet-50 text-violet-600",
    idle: "border-slate-200 bg-white text-slate-700 hover:border-violet-200 hover:bg-violet-50/50",
  },
} as const;

export function ScenarioSwitcher({
  workspace,
  activeKey,
  onChange,
}: {
  workspace: WorkspaceData;
  activeKey: ScenarioKey;
  onChange: (key: ScenarioKey) => void;
}) {
  const order: ScenarioKey[] = ["chat", "doc", "canvas"];

  return (
    <div className="grid grid-cols-3 gap-2">
      {order.map((key) => {
        const scenario = workspace.scenarios[key];
        const isActive = key === activeKey;

        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            className={cn(
              "flex items-center justify-center gap-2 rounded-[14px] border px-3 py-3 text-[14px] font-semibold transition",
              isActive ? buttonStyles[key].active : buttonStyles[key].idle,
            )}
          >
            <span className="text-[12px]">{scenario.switcherLabel}</span>
            <span>{scenario.label}</span>
          </button>
        );
      })}
    </div>
  );
}
