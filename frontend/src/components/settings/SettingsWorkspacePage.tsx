"use client";

import Link from "next/link";

import { WorkspacePageHeader } from "@/components/workspace/workspace-page-framing";
import type { SessionListPageData } from "@/types/session";

const cards = [
  {
    title: "我的资料",
    desc: "头像、姓名与对外展示信息",
    href: "/profile",
    tone: "blue" as const,
  },
  {
    title: "账号与安全",
    desc: "密码、登录设备与第三方绑定",
    href: "/profile/security",
    tone: "slate" as const,
  },
  {
    title: "通知设置",
    desc: "桌面提醒、邮件与飞书推送范围",
    href: "/profile/notifications",
    tone: "emerald" as const,
  },
];

export function SettingsWorkspacePage({ data }: { data: SessionListPageData }) {
  return (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <WorkspacePageHeader
          title="设置"
          description="飞书式工作台统一入口；以下为演示分组，详细表单仍在个人资料子页编辑。"
        />
        <div className="min-h-0 flex-1 overflow-auto px-7 py-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((c) => (
              <Link
                key={c.href}
                href={c.href}
                prefetch={false}
                className={[
                  "group flex flex-col rounded-[22px] border p-5 transition",
                  c.tone === "blue"
                    ? "border-blue-100 bg-blue-50/50 hover:border-blue-200 hover:shadow-md"
                    : c.tone === "emerald"
                      ? "border-emerald-100 bg-emerald-50/40 hover:border-emerald-200 hover:shadow-md"
                      : "border-slate-200 bg-slate-50/50 hover:border-slate-300 hover:shadow-md",
                ].join(" ")}
              >
                <h2 className="text-[15px] font-semibold text-slate-950 group-hover:text-blue-600">{c.title}</h2>
                <p className="mt-2 flex-1 text-[12px] leading-relaxed text-slate-500">{c.desc}</p>
                <span className="mt-4 text-[12px] font-semibold text-blue-600">进入 →</span>
              </Link>
            ))}
          </div>

          <div className="mt-10 rounded-[20px] border border-dashed border-slate-200 bg-slate-50/60 px-5 py-4 text-[12px] text-slate-500">
            <p className="font-semibold text-slate-700">偏好与实验功能</p>
            <p className="mt-1">后续可在此接入主题、语言与 Beta 开关；当前为占位说明。</p>
          </div>
        </div>
      </div>
  );
}
