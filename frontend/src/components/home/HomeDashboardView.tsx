"use client";

import Link from "next/link";

import { cn } from "@/components/UiPrimitives";
import type { SessionItem, SessionListPageData } from "@/types/session";

function SparkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M10 2.5l1.8 4.9 5 1.4-5 1.4L10 14.8 8.2 10 3.2 8.6l5-1.4L10 2.5z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M6 4h6v6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 4l-6 6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function StatCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint: string;
  accent: "blue" | "emerald" | "violet";
}) {
  const ring =
    accent === "blue"
      ? "border-blue-100 bg-white shadow-[0_10px_28px_rgba(37,99,235,0.08)]"
      : accent === "emerald"
        ? "border-emerald-100 bg-white shadow-[0_10px_28px_rgba(16,185,129,0.07)]"
        : "border-violet-100 bg-white shadow-[0_10px_28px_rgba(139,92,246,0.07)]";
  const pill =
    accent === "blue"
      ? "bg-blue-50 text-blue-600"
      : accent === "emerald"
        ? "bg-emerald-50 text-emerald-600"
        : "bg-violet-50 text-violet-600";

  return (
    <div className={cn("flex aspect-square min-w-0 flex-col justify-between rounded-[16px] border px-2.5 py-3 sm:aspect-auto sm:rounded-[22px] sm:px-5 sm:py-4", ring)}>
      <p className="truncate text-[10px] font-medium uppercase tracking-[0.06em] text-slate-400 sm:text-[12px] sm:tracking-[0.12em]">{label}</p>
      <p className="text-[22px] font-semibold tracking-tight text-slate-950 tabular-nums sm:mt-2 sm:text-[28px]">{value}</p>
      <div className={cn("inline-flex max-w-full truncate rounded-full px-1.5 py-0.5 text-[9px] font-semibold sm:mt-3 sm:px-2.5 sm:text-[11px]", pill)}>{hint}</div>
    </div>
  );
}

function SessionTeaserCard({ item }: { item: SessionItem }) {
  return (
    <Link
      href={`/sessions/${encodeURIComponent(item.id)}`}
      prefetch={false}
      className="group flex min-w-[220px] max-w-[280px] flex-1 flex-col rounded-[20px] border border-slate-200/90 bg-white p-4 shadow-[0_6px_20px_rgba(15,23,42,0.04)] transition hover:border-blue-200 hover:shadow-[0_12px_32px_rgba(37,99,235,0.1)]"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="line-clamp-2 min-w-0 text-[14px] font-semibold leading-snug text-slate-900 group-hover:text-blue-600">{item.title}</p>
        <span className="shrink-0 text-slate-300 transition group-hover:text-blue-500">
          <ArrowRightIcon />
        </span>
      </div>
      <p className="mt-2 line-clamp-2 text-[12px] leading-relaxed text-slate-500">{item.summary}</p>
      <div className="mt-4 flex items-center justify-between gap-2">
        <span className="rounded-full bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-600">{item.kindLabel}</span>
        <span className="text-[11px] text-slate-400">{item.updatedAt}</span>
      </div>
    </Link>
  );
}

export function HomeDashboardView({ data }: { data: SessionListPageData }) {
  const allSessions = data.sections.flatMap((s) => s.items);
  const recent = allSessions.slice(0, 4);
  const inProgressCount = allSessions.filter((item) => item.status === "进行中").length;
  const syncedCount = allSessions.filter((item) => item.status === "已同步").length;
  const feishuCount = allSessions.filter((item) => item.source === "飞书").length;
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "早上好" : hour < 18 ? "下午好" : "晚上好";

  return (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <div className="shrink-0 border-b border-slate-200/90 px-7 pb-5 pt-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0">
              <p className="text-[13px] font-medium text-slate-500">
                {greeting}，{data.user.name.split(" ")[0] ?? data.user.name}
              </p>
              <h1 className="mt-1 text-[22px] font-semibold tracking-[-0.04em] text-slate-950">工作台概览</h1>
              <p className="mt-1.5 max-w-xl text-[13px] leading-relaxed text-slate-500">
                从这里进入会话与文稿；左侧导航可随时切换模块。
              </p>
            </div>
            <Link
              href="/sessions"
              prefetch={false}
              className="inline-flex items-center gap-2 rounded-[14px] bg-blue-600 px-5 py-2.5 text-[14px] font-semibold text-white shadow-[0_10px_28px_rgba(37,99,235,0.28)] transition hover:bg-blue-700"
            >
              <SparkIcon />
              进入会话列表
            </Link>
          </div>

          <div className="mt-8 grid grid-cols-3 gap-2 sm:gap-4">
            <StatCard label="进行中会话" value={String(inProgressCount)} hint="来自实时会话" accent="blue" />
            <StatCard label="已同步会话" value={String(syncedCount)} hint="后端最新状态" accent="emerald" />
            <StatCard label="飞书来源" value={String(feishuCount)} hint="由 @机器人 触发" accent="violet" />
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-7 py-6">
          <section>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-[15px] font-semibold text-slate-950">快速开始</h2>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Link
                href="/sessions"
                prefetch={false}
                className="group flex min-h-[74px] flex-col justify-center rounded-[16px] border border-slate-200/90 bg-white px-3.5 py-3 transition hover:border-blue-200 hover:shadow-md sm:min-h-0 sm:rounded-[20px] sm:bg-[linear-gradient(145deg,#ffffff_0%,#f8fafc_100%)] sm:p-5"
              >
                <span className="flex items-center justify-between gap-2 text-[13px] font-semibold text-slate-900">
                  查看会话
                  <span className="text-blue-500 transition group-hover:translate-x-0.5">→</span>
                </span>
                <span className="mt-1 line-clamp-1 text-[11px] leading-snug text-slate-500 sm:text-[12px] sm:leading-relaxed">管理聊天与文稿会话</span>
                <span className="mt-4 hidden text-[12px] font-semibold text-blue-600 sm:inline">打开 →</span>
              </Link>
              <Link
                href="/profile"
                prefetch={false}
                className="group flex min-h-[74px] flex-col justify-center rounded-[16px] border border-slate-200/90 bg-white px-3.5 py-3 transition hover:border-emerald-200 hover:shadow-md sm:col-span-2 sm:min-h-0 sm:rounded-[20px] sm:bg-[linear-gradient(145deg,#ffffff_0%,#f0fdf4_100%)] sm:p-5 lg:col-span-1"
              >
                <span className="flex items-center justify-between gap-2 text-[13px] font-semibold text-slate-900">
                  账户与偏好
                  <span className="text-emerald-500 transition group-hover:translate-x-0.5">→</span>
                </span>
                <span className="mt-1 line-clamp-1 text-[11px] leading-snug text-slate-500 sm:text-[12px] sm:leading-relaxed">资料、通知与安全设置</span>
                <span className="mt-4 hidden text-[12px] font-semibold text-emerald-600 sm:inline">设置 →</span>
              </Link>
            </div>
          </section>

          <section className="mt-10">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-[15px] font-semibold text-slate-950">最近会话</h2>
              <Link href="/sessions" prefetch={false} className="text-[13px] font-semibold text-blue-600 hover:text-blue-700">
                查看全部
              </Link>
            </div>
            <div className="mt-4 flex gap-3 overflow-x-auto pb-2 pt-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              {recent.map((item) => (
                <SessionTeaserCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        </div>
      </div>
  );
}
