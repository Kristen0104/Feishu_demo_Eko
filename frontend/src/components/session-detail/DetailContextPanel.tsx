import type { ReactNode } from "react";

import { SessionDetailData } from "@/types/session-detail";

import { ClockArrowIcon, FeishuSendIcon, MoreIcon, PanelDocIcon } from "@/components/Icons";
import { EvidencePill, HeaderBadge, StatusPill } from "@/components/UiPrimitives";

function PanelBox({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[24px] border border-slate-200/90 bg-white px-5 py-5 shadow-[0_14px_28px_rgba(148,163,184,0.06)]">
      <h3 className="text-[16px] font-semibold text-slate-950">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function DetailContextPanel({ data }: { data: SessionDetailData }) {
  return (
    <aside className="space-y-4">
      <section className="rounded-[24px] border border-slate-200/90 bg-white px-5 py-5 shadow-[0_14px_28px_rgba(148,163,184,0.06)]">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Context & Sync Panel</p>
            <h2 className="mt-3 text-[18px] font-semibold text-slate-950">上下文来源</h2>
          </div>
          <button className="rounded-full border border-transparent p-2 hover:bg-slate-50">
            <MoreIcon />
          </button>
        </div>

        <div className="mt-5 space-y-3">
          {data.contextSources.map((item, index) => (
            <div key={item.id} className={index === 0 ? "space-y-3" : "space-y-3 border-t border-slate-100 pt-3"}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-[12px] border border-slate-200 bg-white text-blue-600 shadow-[0_4px_10px_rgba(15,23,42,0.03)]">
                    <PanelDocIcon tone={index === 2 ? "gray" : "blue"} />
                  </div>
                  <div>
                    <p className="text-[15px] font-semibold text-slate-950">{item.title}</p>
                    <p className="mt-1 text-[13px] leading-6 text-slate-500">{item.description}</p>
                  </div>
                </div>
                <StatusPill status={item.status} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <PanelBox title="来源证据">
        <div className="space-y-3">
          {data.sourceEvidence.map((item) => (
            <div key={item.id} className="flex items-start justify-between gap-3 rounded-[18px] border border-slate-200 bg-white px-4 py-3.5">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-[12px] border border-slate-200 bg-white text-blue-600 shadow-[0_4px_10px_rgba(15,23,42,0.03)]">
                  <PanelDocIcon tone="blue" />
                </div>
                <div>
                  <p className="text-[15px] font-semibold text-slate-950">{item.title}</p>
                  <p className="mt-1.5 text-[12px] leading-6 text-slate-500">{item.description}</p>
                </div>
              </div>
              <EvidencePill tone={item.tone}>
                {item.tone === "chat" ? "聊天" : item.tone === "document" ? "文档" : "记录"}
              </EvidencePill>
            </div>
          ))}
        </div>
      </PanelBox>

      <PanelBox title="同步动作">
        <div className="space-y-3">
          {data.syncActions.map((item, index) => (
            <div key={item.id} className="flex items-center justify-between rounded-[18px] border border-slate-200 bg-white px-4 py-3.5">
              <div className="flex items-center gap-3">
                {index === 1 ? <FeishuSendIcon /> : <ClockArrowIcon tone={item.status === "warning" ? "orange" : "blue"} />}
                <p className="text-[15px] font-semibold text-slate-950">{item.title}</p>
              </div>
              <StatusPill status={item.status} />
            </div>
          ))}
        </div>
      </PanelBox>

      <PanelBox title="状态">
        <div className="flex flex-wrap gap-2">
          {data.statusBadges.map((item) => (
            <HeaderBadge key={item.label} tone={item.tone}>
              {item.label}
            </HeaderBadge>
          ))}
        </div>
      </PanelBox>

      <PanelBox title="系统说明">
        <p className="text-[13px] leading-6 text-slate-500">{data.systemNote}</p>
      </PanelBox>
    </aside>
  );
}
