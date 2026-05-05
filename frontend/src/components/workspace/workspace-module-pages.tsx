import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/components/UiPrimitives";
import { TeamWorkspacePage as LiveTeamWorkspacePage } from "@/components/workspace/team-workspace-page";
import { WorkspacePageHeader } from "@/components/workspace/workspace-page-framing";
import type { SessionItem, SessionListPageData, SessionStatus } from "@/types/session";

type DerivedTask = {
  id: string;
  title: string;
  owner: string;
  due: string;
  status: "已完成" | "进行中" | "待处理";
  priority: "高" | "中" | "低";
  href: string;
};

function flattenSessions(data: SessionListPageData): SessionItem[] {
  return data.sections.flatMap((section) => section.items);
}

function taskStatus(status: SessionStatus): DerivedTask["status"] {
  if (status === "已同步") return "已完成";
  if (status === "进行中") return "进行中";
  return "待处理";
}

function taskPriority(item: SessionItem): DerivedTask["priority"] {
  if (item.status === "进行中") return "高";
  if (item.kind === "canvas") return "中";
  return "低";
}

function buildTasks(data: SessionListPageData): DerivedTask[] {
  return flattenSessions(data).slice(0, 8).map((item) => ({
    id: item.id,
    title: `${item.kindLabel}处理：${item.title}`,
    owner: item.participants[0]?.name ?? data.user.name,
    due: item.updatedAt,
    status: taskStatus(item.status),
    priority: taskPriority(item),
    href: `/sessions/${encodeURIComponent(item.id)}`,
  }));
}

function SectionCard({
  title,
  children,
  className,
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[18px] border border-slate-200/90 bg-white shadow-[0_4px_24px_rgba(15,23,42,0.04)]",
        className,
      )}
    >
      <h2 className="border-b border-slate-100 bg-slate-50/80 px-5 py-3 text-[13px] font-semibold text-slate-800">{title}</h2>
      <div className="p-5">{children}</div>
    </section>
  );
}

export function ShareCollaborationPage({ data }: { data: SessionListPageData }) {
  const sessions = flattenSessions(data);
  const shareableCount = sessions.reduce((count, item) => count + 1 + item.preview.relatedItems.length, 0);
  const pendingCount = sessions.filter((item) => item.status !== "已同步").length;
  const collaboratorCount = new Set(sessions.flatMap((item) => item.participants.map((participant) => participant.id))).size;
  const shareRows = sessions.slice(0, 6).map((item) => ({
    id: item.id,
    name: item.title,
    who: data.teamName,
    perm: item.status === "已同步" ? "可查看" : "协作中",
    at: item.updatedAt,
    href: `/sessions/${encodeURIComponent(item.id)}`,
  }));

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <WorkspacePageHeader
        title="分享 / 协作"
        description="从真实同步会话派生可协作对象、待处理状态与近期共享记录。"
        actions={
          <Link href="/sessions" prefetch={false} className="rounded-[12px] bg-blue-600 px-4 py-2 text-[13px] font-semibold text-white shadow-sm transition hover:bg-blue-700">
            从会话继续协作
          </Link>
        }
      />
      <div className="min-h-0 flex-1 space-y-5 overflow-auto px-7 py-6">
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-[16px] border border-slate-200/90 bg-gradient-to-br from-white to-slate-50/80 p-5">
            <p className="text-[12px] font-medium uppercase tracking-wide text-slate-400">可分享对象</p>
            <p className="mt-2 text-[28px] font-semibold tabular-nums text-slate-950">{shareableCount}</p>
            <p className="mt-1 text-[12px] text-slate-500">包含文档、会话与画布节点</p>
          </div>
          <div className="rounded-[16px] border border-slate-200/90 bg-gradient-to-br from-white to-blue-50/50 p-5">
            <p className="text-[12px] font-medium uppercase tracking-wide text-slate-400">待处理会话</p>
            <p className="mt-2 text-[28px] font-semibold tabular-nums text-blue-600">{pendingCount}</p>
            <p className="mt-1 text-[12px] text-slate-500">草稿、进行中与待处理项</p>
          </div>
          <div className="rounded-[16px] border border-slate-200/90 bg-gradient-to-br from-white to-emerald-50/40 p-5">
            <p className="text-[12px] font-medium uppercase tracking-wide text-slate-400">协作者</p>
            <p className="mt-2 text-[28px] font-semibold tabular-nums text-emerald-700">{collaboratorCount}</p>
            <p className="mt-1 text-[12px] text-slate-500">来自同步会话参与者</p>
          </div>
        </div>

        <SectionCard title="近期共享">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-left text-[13px]">
              <thead className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="pb-3 pr-4 font-semibold">名称</th>
                  <th className="pb-3 pr-4 font-semibold">共享给</th>
                  <th className="pb-3 pr-4 font-semibold">权限</th>
                  <th className="pb-3 font-semibold">更新时间</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                {shareRows.map((row) => (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="py-3 pr-4 font-medium text-slate-900">
                      <Link href={row.href} prefetch={false} className="hover:text-blue-600 hover:underline">
                        {row.name}
                      </Link>
                    </td>
                    <td className="py-3 pr-4">{row.who}</td>
                    <td className="py-3 pr-4">
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-semibold text-slate-600">{row.perm}</span>
                    </td>
                    <td className="py-3 text-slate-500">{row.at}</td>
                  </tr>
                ))}
                {shareRows.length === 0 ? (
                  <tr className="border-t border-slate-100">
                    <td colSpan={4} className="py-10 text-center text-[13px] text-slate-400">暂无可协作会话</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

export function TasksWorkspacePage({ data }: { data: SessionListPageData }) {
  const tasks = buildTasks(data);
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <WorkspacePageHeader
        title="任务"
        description="跨会话、文稿与画布的执行项聚合视图；当前从后端同步会话状态实时派生。"
        actions={
          <Link
            href="/sessions"
            prefetch={false}
            className="rounded-[12px] border border-slate-200 bg-white px-4 py-2 text-[13px] font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            查看会话
          </Link>
        }
      />
      <div className="min-h-0 flex-1 overflow-auto px-7 py-6">
        <div className="mb-4 flex flex-wrap gap-2">
          {["全部", "我负责的", "今日到期", "已完成"].map((label, i) => (
            <span
              key={label}
              className={cn(
                "rounded-full px-3 py-1 text-[12px] font-semibold",
                i === 0 ? "bg-blue-50 text-blue-700 ring-1 ring-blue-100" : "text-slate-500 hover:bg-slate-50",
              )}
            >
              {label}
            </span>
          ))}
        </div>
        <div className="space-y-2">
          {tasks.map((t) => (
            <Link
              key={t.id}
              href={t.href}
              prefetch={false}
              className="flex flex-wrap items-center justify-between gap-3 rounded-[16px] border border-slate-200/90 bg-[#fafbfc] px-4 py-3 transition hover:border-slate-300 hover:bg-white"
            >
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-semibold text-slate-900">{t.title}</p>
                <p className="mt-0.5 text-[12px] text-slate-500">
                  负责人 {t.owner} · 截止 {t.due}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-white px-2.5 py-0.5 text-[11px] font-semibold text-slate-600 ring-1 ring-slate-200">{t.priority}</span>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
                    t.status === "已完成"
                      ? "bg-emerald-50 text-emerald-700"
                      : t.status === "进行中"
                        ? "bg-blue-50 text-blue-700"
                        : "bg-amber-50 text-amber-800",
                  )}
                >
                  {t.status}
                </span>
              </div>
            </Link>
          ))}
          {tasks.length === 0 ? (
            <div className="rounded-[16px] border border-dashed border-slate-200 bg-slate-50/60 px-4 py-10 text-center">
              <p className="text-[14px] font-semibold text-slate-700">暂无任务</p>
              <p className="mt-1 text-[12px] text-slate-400">后端同步会话出现后，会自动派生成待办。</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function TeamWorkspacePage() {
  return <LiveTeamWorkspacePage />;
}

export function AppsWorkspacePage({ data }: { data: SessionListPageData }) {
  const apps = [
    {
      title: "Tldraw 画布",
      desc: "全屏故事板与 Agent 生长演示",
      href: "/canvas",
      tone: "violet" as const,
    },
    {
      title: "会话列表",
      desc: "管理聊天、文稿与画布会话",
      href: "/sessions",
      tone: "blue" as const,
    },
    {
      title: "文档中心",
      desc: "集中查看飞书与会话生成的文稿",
      href: "/documents",
      tone: "sky" as const,
    },
    {
      title: "个人资料",
      desc: `${data.user.name} 的通知与安全`,
      href: "/profile",
      tone: "emerald" as const,
    },
  ];
  const ring: Record<(typeof apps)[number]["tone"], string> = {
    violet: "hover:border-violet-200 hover:shadow-[0_12px_28px_rgba(139,92,246,0.12)]",
    blue: "hover:border-blue-200 hover:shadow-[0_12px_28px_rgba(37,99,235,0.1)]",
    sky: "hover:border-sky-200 hover:shadow-[0_12px_28px_rgba(14,165,233,0.1)]",
    emerald: "hover:border-emerald-200 hover:shadow-[0_12px_28px_rgba(16,185,129,0.1)]",
  };
  const cta: Record<(typeof apps)[number]["tone"], string> = {
    violet: "text-violet-600",
    blue: "text-blue-600",
    sky: "text-sky-600",
    emerald: "text-emerald-600",
  };
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <WorkspacePageHeader
        title="应用"
        description={`工作台快捷入口；当前已同步 ${flattenSessions(data).length} 个会话。`}
      />
      <div className="min-h-0 flex-1 overflow-auto px-7 py-6">
        <div className="grid gap-4 sm:grid-cols-2">
          {apps.map((app) => (
            <Link
              key={app.href}
              href={app.href}
              prefetch={false}
              className={cn(
                "flex flex-col rounded-[20px] border border-slate-200/90 bg-[linear-gradient(145deg,#ffffff_0%,#f8fafc_100%)] p-5 transition",
                ring[app.tone],
              )}
            >
              <span className="text-[15px] font-semibold text-slate-900">{app.title}</span>
              <span className="mt-1 text-[13px] leading-relaxed text-slate-500">{app.desc}</span>
              <span className={cn("mt-4 text-[13px] font-semibold", cta[app.tone])}>打开 →</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
