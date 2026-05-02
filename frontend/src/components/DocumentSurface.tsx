import { ScenarioData } from "@/types/workspace";

import { AccentPill } from "./UiPrimitives";

export function DocumentSurface({ scenario }: { scenario: ScenarioData }) {
  if (scenario.output.kind !== "doc") return null;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-[18px] font-semibold text-slate-950">{scenario.output.title}</h3>
          <p className="mt-2 text-[13px] text-slate-500">{scenario.output.description}</p>
        </div>
        <AccentPill tone={scenario.accent}>{scenario.output.badge}</AccentPill>
      </div>

      <div className="rounded-[24px] border border-slate-200 bg-white px-8 py-8 shadow-[0_8px_24px_rgba(15,23,42,0.03)]">
        <h4 className="text-[24px] font-semibold tracking-[-0.04em] text-slate-950">
          {scenario.output.documentTitle}
        </h4>

        <div className="mt-7 space-y-7">
          {scenario.output.sections.map((section, si) => (
            <section key={`sec-${si}-${section.title}`}>
              <h5 className="text-[18px] font-semibold text-slate-950">{section.title}</h5>
              {section.body && <p className="mt-3 text-[15px] leading-8 text-slate-600">{section.body}</p>}
              {section.bullets && (
                <ul className="mt-4 space-y-3 pl-5 text-[14px] leading-7 text-slate-600">
                  {section.bullets.map((item, bi) => (
                    <li key={`sec-${si}-li-${bi}`} className="list-disc">
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
