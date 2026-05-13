"use client";

import Link from "next/link";

import { WorkspacePageHeader } from "@/components/workspace/workspace-page-framing";
import type { SessionListPageData } from "@/types/session";

const cards = [
  {
    title: "我的资料",
    desc: "姓名与邮箱读取后端登录身份；其他字段为本地覆盖",
    href: "/profile",
    tone: "blue" as const,
    icon: "user" as const,
  },
  {
    title: "账号与安全",
    desc: "当前仅展示本地安全偏好；密码与设备管理未接后端",
    href: "/profile/security",
    tone: "slate" as const,
    icon: "shield" as const,
  },
  {
    title: "通知设置",
    desc: "通知开关保存到本机，暂未回写后端通知服务",
    href: "/profile/notifications",
    tone: "emerald" as const,
    icon: "bell" as const,
  },
];

function InfoIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 30 30" fill="none" aria-hidden="true">
      <circle cx="15" cy="15" r="13.2" stroke="currentColor" strokeWidth="2.4" />
      <path d="M15 13.8v8" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="15" cy="9.5" r="1.5" fill="currentColor" />
    </svg>
  );
}

function CardIcon({ type, tone }: { type: (typeof cards)[number]["icon"]; tone: (typeof cards)[number]["tone"] }) {
  const colorClass = tone === "blue" ? "text-blue-600" : tone === "emerald" ? "text-emerald-600" : "text-slate-800";
  if (type === "shield") {
    return (
      <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] bg-gradient-to-br from-slate-50 to-slate-100 sm:h-[72px] sm:w-[72px] sm:rounded-[22px] ${colorClass}`}>
        <svg width="32" height="32" viewBox="0 0 38 38" fill="none" aria-hidden="true">
          <path d="M19 5.5 8.5 10v8.4c0 6.7 4.2 12.6 10.5 15 6.3-2.4 10.5-8.3 10.5-15V10L19 5.5Z" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round" />
          <rect x="14.3" y="17.2" width="9.4" height="8.6" rx="2" stroke="currentColor" strokeWidth="2.2" />
          <path d="M16.2 17.2v-2.1a2.8 2.8 0 0 1 5.6 0v2.1" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        </svg>
      </span>
    );
  }
  if (type === "bell") {
    return (
      <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] bg-gradient-to-br from-emerald-50 to-green-50 sm:h-[72px] sm:w-[72px] sm:rounded-[22px] ${colorClass}`}>
        <svg width="32" height="32" viewBox="0 0 38 38" fill="none" aria-hidden="true">
          <path d="M12.2 16.4a6.8 6.8 0 0 1 13.6 0v4.1l2.4 4.7H9.8l2.4-4.7v-4.1Z" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
          <path d="M15.6 27.8a3.6 3.6 0 0 0 6.8 0" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M19 7.4V5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </span>
    );
  }
  return (
    <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] bg-gradient-to-br from-blue-50 to-slate-100 sm:h-[72px] sm:w-[72px] sm:rounded-[22px] ${colorClass}`}>
      <svg width="32" height="32" viewBox="0 0 38 38" fill="none" aria-hidden="true">
        <circle cx="19" cy="14.2" r="5.8" stroke="currentColor" strokeWidth="2.7" />
        <path d="M9.8 31.2c.9-6 4.3-9.2 9.2-9.2s8.3 3.2 9.2 9.2" stroke="currentColor" strokeWidth="2.7" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export function SettingsWorkspacePage({ data }: { data: SessionListPageData }) {
  return (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[#F8FAFC] lg:bg-white">
        <div className="hidden lg:block">
        <WorkspacePageHeader
          title="设置"
          description="飞书式工作台统一入口；真实登录身份已接入，安全与通知仍标记为本地偏好。"
        />
        </div>
        <div className="min-h-0 flex-1 overflow-auto px-4 py-3 sm:px-6 sm:py-5 lg:px-7 lg:py-6">
          <div className="mb-4 rounded-[20px] border border-amber-200/80 bg-[#FFF9EC] px-4 py-3.5 text-amber-950 shadow-[0_10px_28px_rgba(251,191,36,0.10)] sm:mb-6 sm:rounded-[24px] sm:px-5 sm:py-5 lg:mb-5 lg:rounded-[18px] lg:px-4 lg:py-3">
            <div className="flex items-start gap-3 sm:gap-4">
              <span className="mt-0.5 shrink-0 text-amber-500">
                <InfoIcon />
              </span>
              <div className="min-w-0">
                <p className="text-[18px] font-semibold leading-tight tracking-[-0.02em] text-slate-950 sm:text-[20px] lg:text-[13px] lg:tracking-normal lg:text-amber-900">能力边界</p>
                <p className="mt-2.5 text-[13px] leading-6 text-slate-700 sm:mt-4 sm:text-[15px] sm:leading-8 lg:mt-1 lg:text-[13px] lg:leading-normal lg:text-amber-900">
                  个人资料页会读取后端当前用户；账号安全、通知和实验功能当前仍是浏览器本地状态，不代表真实企业后台配置。
                </p>
              </div>
            </div>
          </div>
          <div className="grid gap-3.5 sm:gap-5 lg:grid-cols-3">
            {cards.map((c) => (
              <Link
                key={c.href}
                href={c.href}
                prefetch={false}
                className={[
                  "group flex min-h-[112px] items-center gap-4 rounded-[20px] border border-slate-200/80 bg-white px-4 py-4 shadow-[0_14px_32px_rgba(15,23,42,0.07)] transition hover:border-blue-200 hover:shadow-[0_20px_46px_rgba(37,99,235,0.12)] sm:min-h-[154px] sm:gap-5 sm:rounded-[24px] sm:px-5 sm:py-6 sm:shadow-[0_18px_42px_rgba(15,23,42,0.08)] lg:min-h-0 lg:flex-col lg:items-start lg:gap-0 lg:rounded-[22px] lg:p-5 lg:shadow-none",
                  c.tone === "blue"
                    ? ""
                    : c.tone === "emerald"
                      ? "hover:border-emerald-200 hover:shadow-[0_20px_46px_rgba(16,185,129,0.10)]"
                      : "hover:border-slate-300",
                ].join(" ")}
              >
                <CardIcon type={c.icon} tone={c.tone} />
                <div className="min-w-0 flex-1 lg:mt-4">
                  <h2 className="text-[17px] font-semibold leading-tight tracking-[-0.02em] text-slate-950 group-hover:text-blue-600 sm:text-[20px] lg:text-[15px]">{c.title}</h2>
                  <p className="mt-1.5 text-[13px] leading-5 text-slate-500 sm:mt-3 sm:text-[15px] sm:leading-7 lg:mt-2 lg:text-[12px] lg:leading-relaxed">{c.desc}</p>
                </div>
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 text-[22px] leading-none text-slate-400 transition group-hover:border-blue-200 group-hover:text-blue-600 sm:h-11 sm:w-11 sm:text-[26px] lg:hidden">
                  ›
                </span>
              </Link>
            ))}
          </div>

          <div className="mt-3.5 rounded-[20px] border border-slate-200/80 bg-white px-4 py-3.5 text-[13px] text-slate-500 shadow-[0_14px_32px_rgba(15,23,42,0.07)] sm:mt-5 sm:rounded-[24px] sm:px-5 sm:py-5 sm:text-[14px] sm:shadow-[0_18px_42px_rgba(15,23,42,0.08)] lg:mt-10 lg:rounded-[20px] lg:border-dashed lg:bg-slate-50/60 lg:px-5 lg:py-4 lg:text-[12px] lg:shadow-none">
            <p className="text-[16px] font-semibold text-slate-950 sm:text-[18px] lg:text-[12px] lg:text-slate-700">偏好与实验功能</p>
            <p className="mt-1.5 leading-6 sm:mt-2 sm:leading-7 lg:mt-1 lg:leading-normal">后续可在此接入主题、语言与 Beta 开关；当前不发起网络请求。</p>
          </div>
          <div className="mt-4 h-16 border-t border-slate-200/80 lg:hidden" aria-hidden="true" />
        </div>
      </div>
  );
}
