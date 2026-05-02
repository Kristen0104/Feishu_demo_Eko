import { ScenarioData } from "@/types/workspace";

import { NodeGlyph } from "./Icons";
import { AccentPill } from "./UiPrimitives";

export function CanvasSurface({ scenario }: { scenario: ScenarioData }) {
  if (scenario.output.kind !== "canvas") return null;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-[18px] font-semibold text-slate-950">{scenario.output.title}</h3>
          <p className="mt-2 text-[13px] text-slate-500">{scenario.output.description}</p>
        </div>
        <button
          type="button"
          className="rounded-full border border-violet-200 bg-violet-50 px-4 py-2 text-[13px] font-semibold text-violet-600"
        >
          {scenario.output.buttonLabel}
        </button>
      </div>

      <div className="rounded-[24px] border border-dashed border-slate-200 bg-[radial-gradient(circle_at_top,#F8FAFF_0%,#F7FAFF_42%,#F4F7FC_100%)] p-5 shadow-[0_8px_24px_rgba(15,23,42,0.03)]">
        <div className="grid gap-4 md:grid-cols-3">
          {scenario.output.nodes.slice(0, 3).map((node, index) => (
            <div key={node.id} className="relative">
              {index < 2 && (
                <div className="absolute right-[-20px] top-1/2 hidden h-[2px] w-8 -translate-y-1/2 bg-slate-300 md:block" />
              )}
              <div className="relative rounded-[22px] border border-slate-200 bg-white px-5 py-5 shadow-[0_8px_22px_rgba(15,23,42,0.04)]">
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-[14px] font-semibold text-slate-700">
                    {node.index}
                  </span>
                  <NodeGlyph type={node.icon} />
                </div>
                <h4 className="mt-4 text-[17px] font-semibold text-slate-950">{node.title}</h4>
                <ul className="mt-4 space-y-2 text-[13px] leading-6 text-slate-600">
                  {node.bullets.map((bullet, bi) => (
                    <li key={`${node.id}-b-${bi}`}>• {bullet}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <div className="my-3 hidden justify-center md:flex">
          <div className="h-6 w-[66%] rounded-b-[20px] border-b border-dashed border-slate-300" />
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {scenario.output.nodes.slice(3).map((node, index) => (
            <div key={node.id} className="relative">
              {index < 2 && (
                <div className="absolute right-[-20px] top-1/2 hidden h-[2px] w-8 -translate-y-1/2 bg-slate-300 md:block" />
              )}
              <div className="relative rounded-[22px] border border-slate-200 bg-white px-5 py-5 shadow-[0_8px_22px_rgba(15,23,42,0.04)]">
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-[14px] font-semibold text-slate-700">
                    {node.index}
                  </span>
                  <NodeGlyph type={node.icon} />
                </div>
                <h4 className="mt-4 text-[17px] font-semibold text-slate-950">{node.title}</h4>
                <ul className="mt-4 space-y-2 text-[13px] leading-6 text-slate-600">
                  {node.bullets.map((bullet, bi) => (
                    <li key={`${node.id}-b-${bi}`}>• {bullet}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {scenario.output.flowCards.map((item) => (
            <div key={item.id} className="rounded-[18px] border border-slate-200 bg-white px-4 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">{item.title}</p>
              <p className="mt-2 text-[13px] text-slate-600">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
