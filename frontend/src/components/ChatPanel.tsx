import { MoreIcon } from "@/components/Icons";
import { ScenarioKey, WorkspaceData } from "@/types/workspace";

import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import { ScenarioSwitcher } from "./ScenarioSwitcher";
import { Card, PanelTitle } from "./UiPrimitives";

export function ChatPanel({
  workspace,
  activeKey,
  onChange,
}: {
  workspace: WorkspaceData;
  activeKey: ScenarioKey;
  onChange: (key: ScenarioKey) => void;
}) {
  const scenario = workspace.scenarios[activeKey];

  return (
    <Card className="h-full p-5">
      <PanelTitle
        eyebrow="飞书 / 模拟 IM"
        title={scenario.chatPanelTitle}
        action={
          <button
            type="button"
            className="rounded-full border border-transparent p-2 transition hover:bg-slate-50"
            aria-label="more"
          >
            <MoreIcon />
          </button>
        }
      />

      <div className="mt-5">
        <ScenarioSwitcher workspace={workspace} activeKey={activeKey} onChange={onChange} />
      </div>

      <div className="mt-6 flex items-center justify-between">
        <h3 className="text-[17px] font-semibold text-slate-950">{scenario.groupName}</h3>
        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[12px] font-medium text-slate-500">
          模拟在线
        </span>
      </div>

      <div className="mt-5 flex h-[calc(100%-176px)] flex-col">
        <div className="flex-1 overflow-y-auto pr-1">
          <MessageList scenario={scenario} />
        </div>

        <div className="mt-5">
          <MessageInput tone={scenario.accent} />
        </div>
      </div>
    </Card>
  );
}
