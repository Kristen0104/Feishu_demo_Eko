import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/components/UiPrimitives";
import { WorkspacePageHeader } from "@/components/workspace/workspace-page-framing";
import type { SessionListPageData } from "@/types/session";

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
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <WorkspacePageHeader
        title="分享 / 协作"
        description="与团队共享链接、管理协作者与对外可见范围；与飞书生态保持一致的可见性模型（演示数据）。"
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
            <p className="mt-2 text-[28px] font-semibold tabular-nums text-slate-950">18</p>
            <p className="mt-1 text-[12px] text-slate-500">包含文档、会话与画布节点</p>
          </div>
          <div className="rounded-[16px] border border-slate-200/90 bg-gradient-to-br from-white to-blue-50/50 p-5">
            <p className="text-[12px] font-medium uppercase tracking-wide text-slate-400">待处理邀请</p>
            <p className="mt-2 text-[28px] font-semibold tabular-nums text-blue-600">3</p>
            <p className="mt-1 text-[12px] text-slate-500">来自组织内成员</p>
          </div>
          <div className="rounded-[16px] border border-slate-200/90 bg-gradient-to-br from-white to-emerald-50/40 p-5">
            <p className="text-[12px] font-medium uppercase tracking-wide text-slate-400">外部访客</p>
            <p className="mt-2 text-[28px] font-semibold tabular-nums text-emerald-700">5</p>
            <p className="mt-1 text-[12px] text-slate-500">具备只读或评论权限</p>
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
                {[
                  { name: "Q2 增长复盘", who: data.teamName, perm: "可编辑", at: "今天 09:12" },
                  { name: "客户提案 · 草稿", who: "外部评审组", perm: "可评论", at: "昨天" },
                  { name: "画布 · 故事板 v3", who: "设计协作空间", perm: "可查看", at: "周一" },
                ].map((row, rowIdx) => (
                  <tr key={`share-row-${rowIdx}-${row.name}`} className="border-t border-slate-100">
                    <td className="py-3 pr-4 font-medium text-slate-900">{row.name}</td>
                    <td className="py-3 pr-4">{row.who}</td>
                    <td className="py-3 pr-4">
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-semibold text-slate-600">{row.perm}</span>
                    </td>
                    <td className="py-3 text-slate-500">{row.at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

export function TasksWorkspacePage({ data }: { data: SessionListPageData }) {
  const tasks = [
    { id: "t1", title: "同步飞书文档目录结构", owner: data.user.name.split(" ")[0] ?? data.user.name, due: "今天", status: "进行中", priority: "高" },
    { id: "t2", title: "审核画布节点命名规范", owner: "Leo", due: "明天", status: "待处理", priority: "中" },
    { id: "t3", title: "整理会话路由标签", owner: "Mia", due: "周五", status: "已完成", priority: "低" },
  ];
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <WorkspacePageHeader
        title="任务"
        description="跨会话与文档的执行项聚合视图；状态变更将回写到协作动态（演示）。"
        actions={
          <button
            type="button"
            className="rounded-[12px] border border-slate-200 bg-white px-4 py-2 text-[13px] font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            新建任务
          </button>
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
            <div
              key={t.id}
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
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function TeamWorkspacePage({ data }: { data: SessionListPageData }) {
  const members = [
    { id: "cur", name: data.user.name, role: "负责人", initials: data.user.initials, online: true },
    { id: "leo", name: "Leo Zhang", role: "研发", initials: "LZ", online: true },
    { id: "mia", name: "Mia Wu", role: "设计", initials: "MW", online: false },
    { id: "ella", name: "Ella Wang", role: "增长", initials: "EW", online: false },
  ];
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <WorkspacePageHeader
        title="团队"
        description={`当前空间：${data.teamName} · ${data.teamMembersLabel}`}
        actions={
          <button
            type="button"
            className="rounded-[12px] bg-blue-600 px-4 py-2 text-[13px] font-semibold text-white shadow-sm transition hover:bg-blue-700"
          >
            邀请成员
          </button>
        }
      />
      <div className="min-h-0 flex-1 overflow-auto px-7 py-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {members.map((m) => (
            <div
              key={m.id}
              className="flex items-center gap-3 rounded-[18px] border border-slate-200/90 bg-white p-4 shadow-[0_4px_18px_rgba(15,23,42,0.04)]"
            >
              <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[14px] font-semibold text-slate-700">
                {m.initials}
                {m.online ? (
                  <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
                ) : (
                  <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white bg-slate-300" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] font-semibold text-slate-950">{m.name}</p>
                <p className="text-[12px] text-slate-500">{m.role}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
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
        description="在工作台内安装与启用的扩展能力；以下为演示快捷入口。"
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
