import { ScenarioData, HeaderBadge as HeaderBadgeType } from "@/types/workspace";

import { MoreIcon } from "./Icons";
import { ContextSources } from "./ContextSources";
import { SourceEvidence } from "./SourceEvidence";
import { StatusBadges } from "./StatusBadges";
import { SyncActions } from "./SyncActions";
import { Card, PanelTitle } from "./UiPrimitives";

export function ContextSyncPanel({
  scenario,
  footerBadges,
  systemNote,
}: {
  scenario: ScenarioData;
  footerBadges: HeaderBadgeType[];
  systemNote: string;
}) {
  return (
    <Card className="h-full p-5">
      <PanelTitle
        eyebrow="上下文与同步面板"
        title="上下文与同步"
        action={
          <button type="button" className="rounded-full border border-transparent p-2 hover:bg-slate-50">
            <MoreIcon />
          </button>
        }
      />

      <div className="mt-5 space-y-5">
        <section>
          <h3 className="text-[16px] font-semibold text-slate-950">上下文来源</h3>
          <div className="mt-3">
            <ContextSources items={scenario.contextSources} />
          </div>
        </section>

        <section>
          <h3 className="text-[16px] font-semibold text-slate-950">来源证据</h3>
          <div className="mt-3">
            <SourceEvidence items={scenario.sourceEvidence} />
          </div>
        </section>

        <section>
          <h3 className="text-[16px] font-semibold text-slate-950">同步动作</h3>
          <div className="mt-3">
            <SyncActions items={scenario.syncActions} />
          </div>
        </section>

        <section>
          <h3 className="text-[16px] font-semibold text-slate-950">状态</h3>
          <div className="mt-3">
            <StatusBadges items={footerBadges} />
          </div>
        </section>

        <section>
          <h3 className="text-[16px] font-semibold text-slate-950">系统说明</h3>
          <p className="mt-3 text-[13px] leading-6 text-slate-500">{systemNote}</p>
        </section>
      </div>
    </Card>
  );
}
