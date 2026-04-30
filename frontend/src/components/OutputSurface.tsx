import { ScenarioData } from "@/types/workspace";

import { CanvasSurface } from "./CanvasSurface";
import { Card, PanelTitle } from "./UiPrimitives";
import { ChatReplySurface } from "./ChatReplySurface";
import { DocumentSurface } from "./DocumentSurface";

export function OutputSurface({ scenario }: { scenario: ScenarioData }) {
  return (
    <Card className="p-6">
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
        输出面板
      </p>

      <div className="mt-5">
        {scenario.output.kind === "chat" && <ChatReplySurface scenario={scenario} />}
        {scenario.output.kind === "doc" && <DocumentSurface scenario={scenario} />}
        {scenario.output.kind === "canvas" && <CanvasSurface scenario={scenario} />}
      </div>
    </Card>
  );
}
