import { WorkflowStep } from "@/types/workspace";

import { WorkflowStatusIcon } from "./Icons";

const lineColor = {
  completed: "bg-emerald-300/95",
  running: "bg-blue-200/95",
  pending: "bg-slate-200/95",
  warning: "bg-amber-200/95",
} as const;

export function Stepper({ steps }: { steps: WorkflowStep[] }) {
  return (
    <div className="mt-3">
      <div className="grid grid-cols-6 gap-1.5">
        {steps.map((step, index) => (
          <div key={step.id} className="relative flex flex-col items-center text-center">
            {index < steps.length - 1 && (
              <div className="absolute left-[calc(50%+16px)] top-[16px] flex w-[calc(100%-32px)] items-center">
                <span className={`h-[2px] flex-1 rounded-full ${lineColor[step.status]} shadow-[0_1px_4px_rgba(148,163,184,0.12)]`} />
                <span className="ml-1 inline-block h-0 w-0 border-y-[3px] border-y-transparent border-l-[5px] border-l-slate-300" />
              </div>
            )}

            <div className="rounded-full bg-white/95 p-0.5 shadow-[0_6px_14px_rgba(148,163,184,0.12)] ring-1 ring-slate-100/80">
              <WorkflowStatusIcon status={step.status} />
            </div>
            <p className="mt-1.5 max-w-[102px] text-[12px] font-semibold leading-[16px] text-slate-900">
              {step.id}. {step.title}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
