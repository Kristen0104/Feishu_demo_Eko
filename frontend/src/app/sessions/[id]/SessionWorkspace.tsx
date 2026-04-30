"use client";

import { useMemo, useState } from "react";

import type { SessionDetailData } from "@/types/session-detail";

type OutputTabKey = "chat" | "doc" | "canvas";

export function SessionWorkspace({ data }: { data: SessionDetailData }) {
  const [activeTab, setActiveTab] = useState<OutputTabKey>(
    (data.defaultTab as OutputTabKey) ?? "chat",
  );

  const breadcrumb = useMemo(() => {
    const items = Array.isArray(data.breadcrumb) ? data.breadcrumb : ["Eko", "会话", data.title];
    return items.length ? items : ["Eko", "会话", data.title];
  }, [data.breadcrumb, data.title]);

  return (
    <div className="min-h-screen bg-[#f5f7fb] p-4 text-slate-700">
      <div className="mx-auto flex h-[calc(100vh-32px)] max-w-[1560px] overflow-hidden rounded-[26px] border border-[#e7edf5] bg-white shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
        <WorkspaceSidebar navItems={data.navItems} />

        <div className="flex min-w-0 flex-1 flex-col">
          <WorkspaceTopbar breadcrumb={breadcrumb} />

          <div className="grid min-h-0 flex-1 grid-cols-[360px_minmax(520px,1fr)_300px] gap-4 bg-[#f7f9fd] p-4">
            <ConversationPanel title={data.conversationTitle ?? "对话"} messages={data.messages ?? []} />

            <main className="min-w-0 space-y-4">
              <section className="rounded-[22px] border border-[#e7edf5] bg-white shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
                <div className="flex items-start justify-between gap-4 border-b border-[#eef3f9] px-5 py-4">
                  <div className="min-w-0">
                    <h1 className="truncate text-[18px] font-semibold text-slate-900">{data.missionTitle ?? data.title}</h1>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {(data.missionBadges ?? []).slice(0, 3).map((label) => (
                        <Pill key={label} tone={label === "飞书" ? "brand" : label === "聊天" ? "chat" : "info"}>
                          {label}
                        </Pill>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <GhostButton>分享</GhostButton>
                    <GhostButton>导出</GhostButton>
                    <GhostIconButton label="更多">
                      <MoreIcon />
                    </GhostIconButton>
                  </div>
                </div>

                <div className="px-5 py-4">
                  <h2 className="text-[13px] font-semibold text-slate-800">Agent Mission Control</h2>
                  <MissionControlStepper steps={(data.workflow ?? []) as any} />
                  <MissionLegend />
                </div>
              </section>

              <section className="rounded-[22px] border border-[#e7edf5] bg-white shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
                <div className="border-b border-[#eef3f9] px-5 py-4">
                  <h2 className="text-[13px] font-semibold text-slate-800">输出内容</h2>
                  <div className="mt-3 inline-flex rounded-[14px] border border-[#e7edf5] bg-[#f8fafc] p-1">
                    <SegmentTab active={activeTab === "chat"} onClick={() => setActiveTab("chat")} tone="chat">
                      聊天
                    </SegmentTab>
                    <SegmentTab active={activeTab === "doc"} onClick={() => setActiveTab("doc")} tone="doc">
                      文稿
                    </SegmentTab>
                    <SegmentTab active={activeTab === "canvas"} onClick={() => setActiveTab("canvas")} tone="canvas">
                      画布
                    </SegmentTab>
                  </div>
                </div>

                <div className="space-y-4 px-5 py-4">
                  {activeTab === "chat" ? (
                    <OutputResponseCard
                      title={data.chatReply?.title ?? "聊天回复"}
                      body={data.chatReply?.body ?? ""}
                      meta={data.chatReply?.source ?? "来源：飞书即时消息上下文 · 09:13"}
                    />
                  ) : (
                    <OutputResponseCard
                      title={activeTab === "doc" ? "文稿输出" : "画布输出"}
                      body="当前为 Mock 演示：该输出区域将在对应模式下生成内容。"
                      meta="来源：mock 数据 · 即时渲染"
                      muted
                    />
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <PlaceholderCard title="文档区域" subtitle="当前聊天模式未刷新" iconTone="doc" />
                    <PlaceholderCard title="画布区域" subtitle="当前聊天模式未刷新" iconTone="canvas" />
                  </div>
                </div>
              </section>
            </main>

            <aside className="min-w-0 space-y-4">
              <SideCard title="上下文来源">
                <SideList
                  items={(data.contextSources ?? []).map((item: any) => ({
                    id: item.id,
                    title: item.title,
                    status: item.status,
                    icon: <DocIcon />,
                  }))}
                />
              </SideCard>

              <SideCard title="来源证据">
                <SideList
                  items={(data.sourceEvidence ?? []).map((item: any) => ({
                    id: item.id,
                    title: item.title,
                    status: item.tone === "chat" ? "chat" : "neutral",
                    icon: <ChatIcon />,
                    rightTag: item.tone === "chat" ? "聊天" : "来源",
                  }))}
                />
              </SideCard>

              <SideCard title="同步动作">
                <SideList
                  items={(data.syncActions ?? []).map((item: any) => ({
                    id: item.id,
                    title: item.title,
                    status: item.status,
                    icon: <SyncIcon />,
                  }))}
                />
              </SideCard>

              <SideCard title="状态">
                <div className="flex flex-wrap gap-2">
                  {(data.statusBadges ?? []).slice(0, 3).map((b: any) => (
                    <Pill key={b.label} tone={b.tone === "success" ? "success" : b.tone === "info" ? "info" : "neutral"}>
                      {b.label}
                    </Pill>
                  ))}
                </div>
              </SideCard>

              <SideCard title="系统说明">
                <p className="text-[12px] leading-5 text-slate-500">
                  {data.systemNote ??
                    "当前使用 mock 数据支持演示，后续可接飞书 API、Bitable API 与 WebSocket 状态流。"}
                </p>
              </SideCard>
            </aside>
          </div>
        </div>
      </div>
    </div>
  );
}

function WorkspaceSidebar({ navItems }: { navItems?: Array<{ id: string; label: string; active?: boolean }> }) {
  const items =
    navItems?.length
      ? navItems
      : [
          { id: "home", label: "主页" },
          { id: "chat", label: "会话", active: true },
          { id: "doc", label: "文档" },
          { id: "share", label: "分享 / 协作" },
          { id: "task", label: "任务" },
          { id: "team", label: "团队" },
          { id: "apps", label: "应用" },
          { id: "settings", label: "设置" },
        ];

  return (
    <aside className="flex w-[216px] flex-col border-r border-[#e7edf5] bg-[#fafcff] px-3 py-4">
      <div className="mb-6 flex items-center gap-2 px-2">
        <div className="relative h-7 w-7 rounded-full bg-gradient-to-br from-[#2f6bff] via-[#3b82f6] to-[#60a5fa]">
          <span className="absolute left-[7px] top-[6px] block h-3.5 w-2.5 -rotate-[28deg] rounded-[6px] border-2 border-white border-r-0" />
        </div>
        <span className="text-[14px] font-semibold tracking-tight text-slate-900">Eko Workspace</span>
      </div>

      <nav className="space-y-2">
        {items.map((item) => {
          const active = Boolean(item.active) || item.label === "会话";
          return (
            <button
              key={item.id}
              type="button"
              className={`relative flex h-11 w-full items-center gap-3 rounded-xl px-3 text-[14px] transition ${
                active ? "bg-[#edf5ff] text-[#2563eb]" : "text-[#475569] hover:bg-slate-100/80 hover:text-slate-800"
              }`}
            >
              {active ? <span className="absolute left-0 h-5 w-0.5 rounded bg-[#2563eb]" /> : null}
              <span className="grid h-7 w-7 place-items-center rounded-lg border border-[#e7edf5] bg-white">
                <NavMiniIcon id={item.id} active={active} />
              </span>
              <span className="font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto rounded-[14px] border border-[#e7edf5] bg-white px-3 py-2.5 shadow-[0_6px_18px_rgba(15,23,42,0.04)]">
        <div className="flex items-center gap-2.5">
          <div className="relative grid h-9 w-9 place-items-center rounded-full bg-[#e2e8f0] text-[13px] font-semibold text-[#334155]">
            SC
            <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border border-white bg-emerald-500" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">Sarah Chen</p>
            <p className="truncate text-xs text-[#64748b]">在线</p>
          </div>
          <span className="ml-auto text-slate-400">
            <ChevronDown />
          </span>
        </div>
      </div>
    </aside>
  );
}

function WorkspaceTopbar({ breadcrumb }: { breadcrumb: string[] }) {
  return (
    <header className="flex h-[56px] items-center justify-between gap-4 border-b border-[#e7edf5] bg-white px-5">
      <nav className="min-w-0 text-[12px] text-slate-500">
        <ol className="flex min-w-0 items-center gap-2">
          {breadcrumb.map((item, idx) => (
            <li key={`${item}-${idx}`} className="min-w-0 truncate">
              <span className={idx === breadcrumb.length - 1 ? "text-slate-700" : ""}>{item}</span>
              {idx < breadcrumb.length - 1 ? <span className="mx-2 text-slate-300">/</span> : null}
            </li>
          ))}
        </ol>
      </nav>

      <div className="hidden items-center md:flex">
        <div className="flex h-[42px] w-[340px] items-center gap-2 rounded-[12px] border border-[#e7edf5] bg-white px-3 text-[13px] text-slate-500">
          <SearchIcon />
          <span className="text-slate-400">搜索（⌘K）</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <IconButton label="帮助">
          <HelpIcon />
        </IconButton>
        <IconButton label="通知" dot>
          <BellIcon />
        </IconButton>
        <div className="relative h-8 w-8 rounded-full bg-gradient-to-br from-[#ffd9d2] to-[#ffc4b1]">
          <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border border-white bg-emerald-500" />
        </div>
      </div>
    </header>
  );
}

function ConversationPanel({
  title,
  messages,
}: {
  title: string;
  messages: Array<any>;
}) {
  return (
    <section className="flex min-w-0 flex-col overflow-hidden rounded-[24px] border border-[#e7edf5] bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]">
      <header className="flex items-center justify-between border-b border-[#eef3f9] px-4 py-3">
        <h2 className="text-[14px] font-semibold text-slate-900">{title}</h2>
        <div className="flex items-center gap-2 text-slate-400">
          <IconButton label="筛选">
            <FilterIcon />
          </IconButton>
          <IconButton label="更多">
            <MoreIcon />
          </IconButton>
        </div>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {(messages ?? []).map((m: any) => (
          <ChatMessageItem
            key={m.id}
            author={m.author}
            time={m.time}
            body={m.body}
            role={m.role}
            helperText={m.helperText}
            sent={m.sent}
          />
        ))}
      </div>

      <footer className="border-t border-[#eef3f9] p-3">
        <div className="flex items-center gap-2 rounded-full border border-[#e7edf5] bg-white px-3 py-2 shadow-[0_6px_16px_rgba(15,23,42,0.04)]">
          <input
            placeholder="继续让 Eko 处理…"
            className="min-w-0 flex-1 bg-transparent text-[13px] text-slate-700 placeholder:text-slate-400 outline-none"
          />
          <button type="button" className="grid h-8 w-8 place-items-center rounded-full text-slate-400 hover:bg-slate-100">
            <AttachIcon />
          </button>
          <button type="button" className="grid h-8 w-8 place-items-center rounded-full text-slate-400 hover:bg-slate-100">
            <PlusIcon />
          </button>
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-full bg-[#2f6bff] text-white shadow-[0_10px_18px_rgba(47,107,255,0.28)] hover:brightness-[1.02]"
          >
            <SendIcon />
          </button>
        </div>
      </footer>
    </section>
  );
}

function ChatMessageItem(props: any) {
  const isEko = props.role === "eko" || props.author === "Eko";
  return (
    <div className="flex gap-3">
      <div
        className={`grid h-8 w-8 shrink-0 place-items-center rounded-full border ${
          isEko ? "border-[#cfe0ff] bg-[#eef4ff] text-[#2f6bff]" : "border-[#e7edf5] bg-[#f1f5f9] text-slate-600"
        } text-[12px] font-semibold`}
      >
        {String(props.author ?? "").slice(0, 1)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-slate-800">{props.author}</span>
          {props.time ? <span className="text-[11px] text-slate-400">{props.time}</span> : null}
        </div>
        <div
          className={`mt-1 rounded-[14px] px-3 py-2 text-[13px] leading-6 ${
            isEko ? "bg-[#eef4ff] text-slate-700" : "bg-[#f3f6fb] text-slate-700"
          }`}
        >
          {props.body}
        </div>
        {props.helperText ? <p className="mt-1 text-[11px] text-slate-400">{props.helperText}</p> : null}
        {props.sent ? <p className="mt-1 text-[11px] text-slate-400">已发送 · {props.time ?? "—"}</p> : null}
      </div>
    </div>
  );
}

function MissionControlStepper({ steps }: { steps: Array<any> }) {
  return (
    <div className="mt-3 overflow-hidden rounded-[16px] border border-[#e7edf5] bg-white">
      <div className="grid grid-cols-6 gap-0">
        {steps.slice(0, 6).map((step, idx) => (
          <div key={step.id} className="relative border-r border-[#eef3f9] px-3 py-3 last:border-r-0">
            <div className="flex items-start gap-2">
              <StepStatusIcon status={step.status} />
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-slate-800">
                  {idx + 1}. {step.title}
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  {idx === 0 ? "IM 上下文" : idx === 1 ? "当前意图" : idx === 2 ? "RAG" : idx === 3 ? "文稿 / 画布" : idx === 4 ? "Bitable" : "飞书群"}
                </p>
              </div>
            </div>
            {idx < 5 ? <StepperArrow /> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function MissionLegend() {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-slate-500">
      <LegendDot tone="success" label="已完成" />
      <LegendDot tone="info" label="进行中" />
      <LegendDot tone="neutral" label="待处理" />
      <LegendDot tone="warning" label="预警" />
    </div>
  );
}

function OutputResponseCard({ title, body, meta, muted }: any) {
  return (
    <div className="rounded-[18px] border border-[#e7edf5] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[13px] font-semibold text-slate-900">{title}</h3>
          <p className={`mt-2 text-[13px] leading-6 ${muted ? "text-slate-500" : "text-slate-700"}`}>{body}</p>
          <p className="mt-2 text-[11px] text-slate-400">{meta}</p>
        </div>
        <div className="flex items-center gap-1 text-slate-400">
          <GhostIconButton label="点赞">
            <ThumbUpIcon />
          </GhostIconButton>
          <GhostIconButton label="点踩">
            <ThumbDownIcon />
          </GhostIconButton>
          <GhostIconButton label="复制">
            <CopyIcon />
          </GhostIconButton>
        </div>
      </div>
    </div>
  );
}

function PlaceholderCard({ title, subtitle, iconTone }: any) {
  const tone =
    iconTone === "doc"
      ? "border-sky-200 bg-sky-50 text-sky-700"
      : "border-violet-200 bg-violet-50 text-violet-700";

  return (
    <div className="rounded-[16px] border border-[#e7edf5] bg-[#fbfcfe] p-4">
      <div className={`grid h-9 w-9 place-items-center rounded-xl border ${tone} text-sm`}>{iconTone === "doc" ? "▤" : "◉"}</div>
      <p className="mt-3 text-[13px] font-semibold text-slate-800">{title}</p>
      <p className="mt-1 text-[12px] text-slate-500">{subtitle}</p>
    </div>
  );
}

function SideCard({ title, children }: any) {
  return (
    <section className="rounded-[20px] border border-[#e7edf5] bg-white p-4 shadow-[0_8px_22px_rgba(15,23,42,0.04)]">
      <h3 className="text-[13px] font-semibold text-slate-900">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function SideList({ items }: any) {
  return (
    <ul className="space-y-2">
      {items.map((item: any) => (
        <li key={item.id} className="flex items-center justify-between gap-3 rounded-[14px] border border-[#eef3f9] bg-[#fbfcfe] px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-xl border border-[#e7edf5] bg-white text-slate-500">{item.icon}</span>
            <span className="truncate text-[12px] text-slate-700">{item.title}</span>
          </div>
          <div className="shrink-0">
            {item.rightTag ? <Pill tone={item.rightTag === "聊天" ? "chat" : "neutral"}>{item.rightTag}</Pill> : <StatusTag status={item.status} />}
          </div>
        </li>
      ))}
    </ul>
  );
}

function SegmentTab({ active, onClick, tone, children }: any) {
  const activeStyle =
    tone === "chat"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : tone === "doc"
        ? "bg-sky-50 text-sky-700 border-sky-200"
        : "bg-violet-50 text-violet-700 border-violet-200";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex h-9 items-center rounded-[12px] px-4 text-[13px] font-medium transition ${
        active ? `border ${activeStyle}` : "text-slate-500 hover:text-slate-700"
      }`}
    >
      {children}
    </button>
  );
}

function Pill({ tone, children }: any) {
  const style =
    tone === "brand"
      ? "bg-slate-100 text-slate-700"
      : tone === "chat"
        ? "bg-emerald-50 text-emerald-700"
        : tone === "success"
          ? "bg-emerald-50 text-emerald-700"
          : tone === "info"
            ? "bg-sky-50 text-sky-700"
            : "bg-slate-100 text-slate-600";

  return <span className={`inline-flex h-6 items-center rounded-full px-2.5 text-[11px] font-medium ${style}`}>{children}</span>;
}

function StatusTag({ status }: any) {
  const style =
    status === "completed"
      ? "bg-emerald-50 text-emerald-700"
      : status === "running"
        ? "bg-sky-50 text-sky-700"
        : status === "pending"
          ? "bg-slate-100 text-slate-600"
          : "bg-amber-50 text-amber-800";
  const label = status === "completed" ? "已完成" : status === "running" ? "进行中" : status === "pending" ? "待处理" : "预警";
  return <span className={`inline-flex h-6 items-center rounded-full px-2.5 text-[11px] font-medium ${style}`}>{label}</span>;
}

function StepStatusIcon({ status }: any) {
  if (status === "completed") {
    return (
      <span className="grid h-6 w-6 place-items-center rounded-full bg-emerald-50 text-emerald-600">
        <CheckIcon />
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="grid h-6 w-6 place-items-center rounded-full bg-sky-50 text-sky-600">
        <SpinnerIcon />
      </span>
    );
  }
  if (status === "warning") {
    return (
      <span className="grid h-6 w-6 place-items-center rounded-full bg-amber-50 text-amber-700">
        <AlertIcon />
      </span>
    );
  }
  return <span className="h-6 w-6 rounded-full border-2 border-slate-200 bg-white" />;
}

function LegendDot({ tone, label }: any) {
  const cls =
    tone === "success"
      ? "border-emerald-300 bg-emerald-50"
      : tone === "info"
        ? "border-sky-300 bg-sky-50"
        : tone === "warning"
          ? "border-amber-300 bg-amber-50"
          : "border-slate-200 bg-white";

  return (
    <span className="inline-flex items-center gap-2">
      <span className={`h-3 w-3 rounded-full border ${cls}`} />
      <span>{label}</span>
    </span>
  );
}

function GhostButton({ children }: any) {
  return (
    <button
      type="button"
      className="inline-flex h-9 items-center gap-2 rounded-[12px] border border-[#e7edf5] bg-white px-3 text-[13px] text-slate-700 shadow-[0_1px_0_rgba(15,23,42,0.02)] hover:bg-slate-50"
    >
      {children}
    </button>
  );
}

function GhostIconButton({ label, children }: any) {
  return (
    <button
      type="button"
      aria-label={label}
      className="grid h-9 w-9 place-items-center rounded-[12px] border border-[#e7edf5] bg-white text-slate-500 hover:bg-slate-50"
    >
      {children}
    </button>
  );
}

function IconButton({ label, dot, children }: any) {
  return (
    <button
      type="button"
      aria-label={label}
      className="relative grid h-9 w-9 place-items-center rounded-full border border-[#e7edf5] bg-white text-slate-500 hover:bg-slate-50"
    >
      {children}
      {dot ? <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" /> : null}
    </button>
  );
}

function StepperArrow() {
  return <span className="pointer-events-none absolute right-[-8px] top-1/2 h-px w-4 -translate-y-1/2 bg-[#e7edf5]" />;
}

function NavMiniIcon({ id, active }: any) {
  const c = active ? "#2563eb" : "#64748b";
  if (id === "home")
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path d="M4 11.5L12 5l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5V21H5a1 1 0 0 1-1-1v-8.5z" stroke={c} strokeWidth="1.7" />
      </svg>
    );
  if (id === "chat")
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path d="M20 12a6 6 0 0 1-6 6H8l-4 3v-9a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6z" stroke={c} strokeWidth="1.7" />
      </svg>
    );
  if (id === "doc")
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM14 3v6h6" stroke={c} strokeWidth="1.7" />
      </svg>
    );
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 12h12M12 6v12" stroke={c} strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0 text-slate-400">
      <circle cx="11" cy="11" r="6.8" stroke="currentColor" strokeWidth="1.8" />
      <path d="M16 16l4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function HelpIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 18h.01M9.5 9.2a2.8 2.8 0 1 1 4.2 2.5c-.9.5-1.7 1.2-1.7 2.3v.6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6.5 9.5a5.5 5.5 0 0 1 11 0V14l1.5 2v1h-14v-1L6.5 14V9.5zM10 18a2 2 0 0 0 4 0"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 6h16M7 12h10M10 18h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 12h.01M12 12h.01M18 12h.01" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function AttachIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M8 12.5l7.2-7.2a3 3 0 1 1 4.2 4.2L10.8 18a5 5 0 0 1-7.1-7.1L12 2.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 12l16-8-6 16-2.5-6L4 12z" fill="currentColor" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M20 7L10 17l-5-5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 4a8 8 0 1 1-7.6 10" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 9v4m0 4h.01" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M10 3h4l8 18H2L10 3z" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

function ChevronDown() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 10l5 5 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M9 9h10v10H9V9z" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function ThumbUpIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M9 11V21H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h4zm0 0l4-8a2 2 0 0 1 2 2v6h4a2 2 0 0 1 2 2l-2 6a2 2 0 0 1-2 2H9"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M9 13V3H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h4zm0 0l4 8a2 2 0 0 0 2-2v-6h4a2 2 0 0 0 2-2l-2-6a2 2 0 0 0-2-2H9"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM14 3v6h6" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M20 12a6 6 0 0 1-6 6H8l-4 3v-9a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6z" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function SyncIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M20 6v6h-6M4 18v-6h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M20 12a8 8 0 0 0-14.7-4M4 12a8 8 0 0 0 14.7 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

