"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { publishDemoEvent, subscribeDemoEvents, type DemoBusEvent } from "@/lib/demo/demo-bus";

type CardState = {
  statusText: string;
  progress: number;
  done: boolean;
  docUrl?: string;
};

function initialCard(): CardState {
  return { statusText: "正在生成中…", progress: 0.42, done: false };
}

function useDemoCardState(sessionId: string) {
  const [state, setState] = useState<CardState>(() => initialCard());

  useState(() => {
    return subscribeDemoEvents((ev: DemoBusEvent) => {
      if (ev.sessionId !== sessionId) return;
      if (ev.type === "CARD_STATUS") {
        setState((prev) => ({
          ...prev,
          statusText: ev.statusText,
          progress: typeof ev.progress === "number" ? ev.progress : prev.progress,
        }));
      }
      if (ev.type === "PPT_EXPORTED") {
        setState((prev) => ({ ...prev, statusText: `PPTX 已导出：${ev.filename}` }));
      }
      if (ev.type === "ARCHIVED") {
        setState((prev) => ({
          ...prev,
          done: true,
          progress: 1,
          statusText: "✅ 已定稿",
          docUrl: `/knowledge`,
        }));
      }
    });
  });

  return state;
}

export function FeishuMockPage() {
  const sessionId = "demo-canvas";
  const [isOwner, setIsOwner] = useState(true);

  const user = useMemo(() => (isOwner ? { id: "ou_zhangsan", name: "张三" } : { id: "ou_lisi", name: "李四" }), [isOwner]);
  const owner = { id: "ou_zhangsan", name: "张三" };

  const card = useDemoCardState(sessionId);

  const previewHref = useMemo(() => {
    const q = new URLSearchParams();
    q.set("session", sessionId);
    q.set("owner", owner.id);
    q.set("user", user.id);
    return `/preview?${q.toString()}`;
  }, [owner.id, sessionId, user.id]);

  return (
    <main className="min-h-screen bg-[#f5f7fb] p-6 text-slate-800">
      <div className="mx-auto w-full max-w-[1040px] overflow-hidden rounded-[26px] border border-[#e7edf5] bg-white shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
        <header className="flex flex-col gap-3 border-b border-[#eef3f9] px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.22em] text-slate-400">飞书项目群（Mock）</p>
            <p className="mt-1 text-[16px] font-semibold text-slate-900">Eko 演示群 · 项目计划</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setIsOwner((v) => !v)}
              className="rounded-[12px] border border-slate-200 bg-white px-3 py-2 text-[13px] font-semibold text-slate-700 hover:bg-slate-50"
            >
              切换身份：{user.name}
            </button>
            <Link
              href="/sessions/demo-canvas"
              prefetch={false}
              className="rounded-[12px] border border-slate-200 bg-white px-3 py-2 text-[13px] font-semibold text-slate-700 hover:bg-slate-50"
            >
              打开工作台
            </Link>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-0 lg:grid-cols-[1fr_360px]">
          <section className="min-h-[560px] bg-white px-4 py-5 sm:px-6 lg:border-r lg:border-[#eef3f9]">
            <div className="space-y-4">
              <Message name="Leo" time="09:12" text="@Eko 把这个方案做成汇报 PPT" />
              <Message name="Eko" time="09:13" text="收到。我会复用刚才的文档内容，自动切换到画布模式生成 PPT 结构。" eko />
              <ActionCard
                title="🚀 方案汇报 PPT（画布）"
                desc="点击查看预览，实时观摩生成过程。创建者可进入画板编辑。"
                status={card.statusText}
                progress={card.progress}
                primaryLabel="查看预览"
                primaryHref={previewHref}
                secondaryLabel={card.done ? "点击查看知识库" : "查看进度"}
                secondaryOnClick={() =>
                  publishDemoEvent({ type: "CARD_STATUS", sessionId, statusText: "正在同步状态…", progress: Math.min(0.98, card.progress + 0.05) })
                }
                done={card.done}
              />
              <Message name="Mia" time="09:14" text="导出完我就直接拿去汇报了" />
            </div>
          </section>

          <aside className="border-t border-[#eef3f9] bg-[#fbfcfe] px-4 py-5 sm:px-5 lg:border-t-0">
            <h2 className="text-[13px] font-semibold text-slate-900">录屏提示</h2>
            <ul className="mt-3 space-y-2 text-[12px] leading-5 text-slate-600">
              <li>1) 先在这里点「查看预览」进入 /preview</li>
              <li>2) 围观者只读，创建者能看到「🎨进入画板编辑」</li>
              <li>3) 在工作台点击「导出 PPTX / 确认保存」会反推更新这张卡片</li>
            </ul>
            <div className="mt-5 rounded-[14px] border border-slate-200 bg-white p-4 text-[12px] text-slate-600">
              当前身份：<span className="font-semibold text-slate-900">{user.name}</span>
              <div className="mt-2">
                owner：<span className="font-mono">{owner.id}</span>
              </div>
              <div className="mt-1">
                user：<span className="font-mono">{user.id}</span>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}

function Message({ name, time, text, eko }: { name: string; time: string; text: string; eko?: boolean }) {
  return (
    <div className="flex gap-3">
      <div className={`grid h-9 w-9 place-items-center rounded-full border ${eko ? "border-violet-200 bg-violet-50 text-violet-700" : "border-slate-200 bg-slate-50 text-slate-700"} text-[12px] font-semibold`}>
        {name.slice(0, 1)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-slate-900">{name}</span>
          <span className="text-[11px] text-slate-400">{time}</span>
        </div>
        <div className="mt-1 rounded-[16px] border border-slate-200 bg-white px-3 py-2 text-[13px] leading-6 text-slate-700 shadow-[0_6px_14px_rgba(15,23,42,0.03)]">
          {text}
        </div>
      </div>
    </div>
  );
}

function ActionCard(props: {
  title: string;
  desc: string;
  status: string;
  progress: number;
  primaryLabel: string;
  primaryHref: string;
  secondaryLabel: string;
  secondaryOnClick: () => void;
  done?: boolean;
}) {
  return (
    <div className="rounded-[18px] border border-violet-200 bg-gradient-to-br from-violet-50 to-fuchsia-50/70 p-4 shadow-[0_10px_22px_rgba(139,92,246,0.10)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[14px] font-semibold text-slate-950">{props.title}</p>
          <p className="mt-1 text-[12px] leading-5 text-slate-600">{props.desc}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold ${props.done ? "bg-emerald-50 text-emerald-700" : "bg-blue-50 text-blue-700"}`}>
          {props.status}
        </span>
      </div>

      <div className="mt-3">
        <div className="h-2 w-full rounded-full bg-white/70">
          <div className="h-2 rounded-full bg-violet-600 transition-all" style={{ width: `${Math.round(props.progress * 100)}%` }} />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Link
          href={props.primaryHref}
          prefetch={false}
          className="inline-flex h-9 items-center justify-center rounded-full bg-violet-600 px-4 text-[13px] font-semibold text-white shadow-sm hover:bg-violet-700"
        >
          {props.primaryLabel}
        </Link>
        <button
          type="button"
          onClick={props.secondaryOnClick}
          className="inline-flex h-9 items-center justify-center rounded-full border border-slate-200 bg-white px-4 text-[13px] font-semibold text-slate-700 hover:bg-slate-50"
        >
          {props.secondaryLabel}
        </button>
      </div>
    </div>
  );
}

