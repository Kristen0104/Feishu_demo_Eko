"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { useAppStore } from "@/store/app-store";

const MOCK_EMAIL = "sarah.chen@eko.ai";
const DEFAULT_PASSWORD = "eko123456";
const PASSWORD_KEY = "eko:mock-password";
const LAST_LOGIN_KEY = "eko:last-login-email";

function getCurrentMockPassword() {
  if (typeof window === "undefined") return DEFAULT_PASSWORD;
  return window.localStorage.getItem(PASSWORD_KEY) ?? DEFAULT_PASSWORD;
}

function BrandMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 44 44" className={className} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="eko-mark" x1="6" y1="5" x2="37" y2="39" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2084FF" />
          <stop offset="1" stopColor="#2854FF" />
        </linearGradient>
      </defs>
      <rect x="3.5" y="3.5" width="37" height="37" rx="12" fill="url(#eko-mark)" />
      <path
        d="M29.2 14.4c-2.5-2-5.1-3-8-3-4.9 0-8.5 3.6-8.5 8.8s3.6 8.8 8.5 8.8c3 0 5.4-.8 8-2.9l-2.8-3.5c-1.7 1.2-3.2 1.7-5.3 1.7-2 0-3.6-.9-4.2-2.7h11.6c.1-.6.2-1.2.2-1.9 0-1.8-.4-3.5-1.1-5.1H17.2c.6-1.7 2.2-2.8 4-2.8 2 0 3.7.5 5.4 1.8l2.6-3.3Z"
        fill="white"
      />
    </svg>
  );
}

function FeishuLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <path d="M4 7.4c0-1 .8-1.8 1.8-1.8h6.7L8.4 13H5.8A1.8 1.8 0 0 1 4 11.2V7.4Z" fill="#1C8BFF" />
      <path d="M12.2 5.6h5.6c1 0 1.8.8 1.8 1.8v1.8a4 4 0 0 1-4 4h-5l1.6-7.6Z" fill="#35C59D" />
      <path d="M8.6 13.8h10.2a1.8 1.8 0 0 1 1.7 2.4l-.5 1.4a3.4 3.4 0 0 1-3.2 2.3H8.6V13.8Z" fill="#3558FF" />
      <path d="M5 14.2h2.7v5a1.7 1.7 0 0 1-2.7-1.3v-3.7Z" fill="#67D66E" />
    </svg>
  );
}

function GoogleLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <path d="M21.6 12.2c0-.8-.1-1.4-.2-2H12v3.7h5.5a4.7 4.7 0 0 1-2 3.1v2.6h3.3c2-1.9 2.8-4.5 2.8-7.4Z" fill="#4285F4" />
      <path d="M12 22c2.7 0 5-.9 6.7-2.5l-3.3-2.6c-.9.6-2 .9-3.4.9-2.6 0-4.8-1.8-5.5-4.2H3.1v2.7A10.1 10.1 0 0 0 12 22Z" fill="#34A853" />
      <path d="M6.5 13.6a6 6 0 0 1 0-3.2V7.7H3.1a10.1 10.1 0 0 0 0 8.6l3.4-2.7Z" fill="#FBBC05" />
      <path d="M12 6.2c1.5 0 2.8.5 3.8 1.5l2.8-2.8C17 3.3 14.7 2.4 12 2.4A10.1 10.1 0 0 0 3.1 7.7l3.4 2.7c.7-2.4 2.9-4.2 5.5-4.2Z" fill="#EA4335" />
    </svg>
  );
}

function FeatureIcon({
  tone,
  children,
}: {
  tone: "green" | "blue" | "purple";
  children: React.ReactNode;
}) {
  const tones = {
    green: "border-emerald-200/80 bg-emerald-50/80 text-emerald-500 shadow-[0_14px_30px_rgba(16,185,129,0.10)]",
    blue: "border-blue-200/80 bg-blue-50/80 text-blue-500 shadow-[0_14px_30px_rgba(37,99,235,0.10)]",
    purple: "border-violet-200/80 bg-violet-50/80 text-violet-500 shadow-[0_14px_30px_rgba(139,92,246,0.10)]",
  };

  return (
    <div className={`flex h-16 w-16 items-center justify-center rounded-[20px] border ${tones[tone]}`}>
      {children}
    </div>
  );
}

function FloatingIcon({
  className,
  tone,
  children,
}: {
  className: string;
  tone: "green" | "blue" | "purple";
  children: React.ReactNode;
}) {
  const tones = {
    green: "text-emerald-500 shadow-[0_18px_36px_rgba(16,185,129,0.12)]",
    blue: "text-blue-500 shadow-[0_18px_36px_rgba(37,99,235,0.12)]",
    purple: "text-violet-500 shadow-[0_18px_36px_rgba(139,92,246,0.12)]",
  };

  return (
    <div
      className={`pointer-events-none absolute flex h-20 w-20 items-center justify-center rounded-[30px] border border-white/80 bg-white/88 backdrop-blur-sm ${tones[tone]} ${className}`}
    >
      {children}
    </div>
  );
}

export function LoginPage() {
  const router = useRouter();
  const setLogin = useAppStore((state) => state.setLogin);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const currentYear = new Date().getFullYear();

  const loginDisabled = useMemo(() => !email.trim() || !password.trim() || submitting, [email, password, submitting]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    window.setTimeout(() => {
      const currentPassword = getCurrentMockPassword();
      const validEmail = email.trim().toLowerCase() === MOCK_EMAIL;
      const validPassword = password === currentPassword;

      if (!validEmail || !validPassword) {
        setSubmitting(false);
        setError("账号或密码不正确，请重新输入。");
        return;
      }

      if (remember && typeof window !== "undefined") {
        window.localStorage.setItem(LAST_LOGIN_KEY, email.trim().toLowerCase());
      }

      setLogin(email.trim().toLowerCase());
      router.push("/sessions");
    }, 650);
  }

  return (
    <main className="relative min-h-screen bg-[radial-gradient(circle_at_50%_18%,#f8fbff_0%,#edf4ff_42%,#edf2fb_100%)] px-6 pb-6 pt-5 text-slate-900">
      <div className="mx-auto flex h-[calc(100vh-8px)] w-full max-w-[1400px] flex-col">
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(680px,1fr)_500px] items-center gap-x-[72px] px-4 pb-20 pt-3">
          <section className="relative flex min-h-0 flex-col justify-center pl-2 pr-0">
            <div className="relative z-10 max-w-[760px]">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-4">
                  <BrandMark className="h-[38px] w-[38px]" />
                  <span className="text-[35px] font-semibold tracking-[-0.08em] text-slate-950">Eko</span>
                </div>
                <div className="h-7 w-px bg-slate-200" />
                <span className="text-[20px] font-medium tracking-[-0.04em] text-slate-400">AI Workplace</span>
                <span className="inline-flex h-8 items-center rounded-full border border-blue-100 bg-blue-50/85 px-3.5 text-[13px] font-medium text-blue-500 shadow-[0_8px_20px_rgba(59,130,246,0.10)]">
                  AI 工作空间
                </span>
              </div>

              <div className="mt-6">
                <h1 className="flex max-w-[760px] items-center gap-3 text-[52px] font-semibold leading-[1.12] tracking-[-0.05em] text-slate-950">
                  <BrandMark className="h-[42px] w-[42px] shrink-0" />
                  <span>AI，让对话快速转化为工作产出</span>
                </h1>
                <p className="mt-3 max-w-[620px] text-[15px] leading-[1.7] text-slate-500">
                  将聊天或 IM 输入自动路由为聊天、文稿和画布输出，帮助团队更高效协作。
                </p>
              </div>

              <div className="mt-6 space-y-3.5">
                <div className="flex items-start gap-4">
                  <FeatureIcon tone="green">
                    <svg viewBox="0 0 24 24" className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M8 9.5h8" />
                      <path d="M8 13.5h4.2" />
                      <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">把聊天转成可执行结果</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500">
                      将想法、讨论和决策，自动转化为任务、计划、跟进项与落地建议。
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <FeatureIcon tone="blue">
                    <svg viewBox="0 0 24 24" className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M8 3.5h6.3L19.5 8v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6.5 20v-15A1.5 1.5 0 0 1 8 3.5Z" />
                      <path d="M14 3.8V8h4.2" />
                      <path d="M9.2 12.2h5.9" />
                      <path d="M9.2 16h5.9" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">AI 驱动的文稿与画布路由</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500">
                      自动识别内容类型，智能分发到文稿、画布和回复等合适输出形式。
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <FeatureIcon tone="purple">
                    <svg viewBox="0 0 24 24" className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
                      <circle cx="8.2" cy="9.2" r="2.9" />
                      <circle cx="15.9" cy="9.2" r="2.9" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">面向团队的上下文同步</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500">
                      连接工具与知识库，保持信息一致，让团队协作始终基于正确上下文。
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="absolute left-[204px] top-[246px] h-[360px] w-[360px] rounded-full border border-white/40 bg-[radial-gradient(circle_at_center,rgba(191,219,254,0.28)_0%,rgba(191,219,254,0.12)_26%,rgba(255,255,255,0)_72%)] shadow-[0_0_120px_rgba(96,165,250,0.12)]" />
            <div className="absolute left-[236px] top-[280px] h-[300px] w-[300px] rounded-full border border-white/40 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.4)_0%,rgba(255,255,255,0.08)_54%,rgba(255,255,255,0)_100%)]" />
            <div className="absolute left-[266px] top-[310px] h-[246px] w-[246px] rounded-full border border-white/50 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.28)_0%,rgba(255,255,255,0.02)_70%)]" />

            <FloatingIcon className="left-[590px] top-[242px] h-14 w-14 rounded-[22px]" tone="green">
              <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
                <path d="M8 9.5h8" />
                <path d="M8 13.5h4.2" />
                <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
              </svg>
            </FloatingIcon>

            <FloatingIcon className="left-[518px] top-[458px] h-14 w-14 rounded-[22px]" tone="blue">
              <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
                <path d="M8 3.5h6.3L19.5 8v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6.5 20v-15A1.5 1.5 0 0 1 8 3.5Z" />
                <path d="M14 3.8V8h4.2" />
                <path d="M9.2 12.2h5.9" />
                <path d="M9.2 16h5.9" />
              </svg>
            </FloatingIcon>

            <FloatingIcon className="left-[608px] top-[612px] h-14 w-14 rounded-[22px]" tone="purple">
              <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
                <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
                <circle cx="8.2" cy="9.2" r="2.9" />
                <circle cx="15.9" cy="9.2" r="2.9" />
              </svg>
            </FloatingIcon>

            <div className="relative z-10 mt-6 w-[540px] rounded-[24px] border border-white/85 bg-white/88 shadow-[0_24px_64px_rgba(15,23,42,0.09)] backdrop-blur-md scale-[0.86] origin-top-left">
              <div className="grid grid-cols-[154px_1fr]">
                <aside className="border-r border-slate-100 px-4.5 py-5">
                  <div className="flex items-center gap-3">
                    <BrandMark className="h-7 w-7" />
                    <span className="text-[22px] font-semibold tracking-[-0.06em] text-slate-950">Eko</span>
                  </div>
                  <nav className="mt-5 space-y-1.5">
                    {["首页", "对话", "文档", "画布", "任务", "日历", "知识库", "团队", "设置"].map((item, index) => (
                      <div
                        key={item}
                        className={`flex h-8 items-center gap-3 rounded-[12px] px-3 text-[13px] ${
                          index === 0 ? "bg-blue-50 text-blue-600" : "text-slate-500"
                        }`}
                      >
                        <div className={`h-3.5 w-3.5 rounded-full border ${index === 0 ? "border-blue-500" : "border-slate-300"}`} />
                        {item}
                      </div>
                    ))}
                  </nav>
                </aside>

                <div className="px-5 py-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-[30px] font-semibold tracking-[-0.06em] text-slate-950">早上好，欢迎回来👋</h3>
                      <p className="mt-1 text-[12px] text-slate-500">有什么新想法？问问 Eko，或从以下快捷方式开始。</p>
                    </div>
                    <div className="flex items-center gap-3 text-slate-400">
                      <div className="h-5 w-5 rounded-full border border-slate-200" />
                      <div className="flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 text-[12px] font-semibold text-slate-500">
                        SC
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-3 gap-2.5">
                    {[
                      ["新建对话", "与 AI 互动和沟通", "green"],
                      ["新建文档", "创建文档型知识沉淀", "blue"],
                      ["新建画布", "可视化梳理思路流程", "purple"],
                    ].map(([title, desc, tone]) => (
                      <div key={title} className="rounded-[16px] border border-slate-100 bg-white px-3.5 py-3.5 shadow-[0_16px_28px_rgba(15,23,42,0.06)]">
                        <div
                          className={`flex h-8 w-8 items-center justify-center rounded-xl ${
                            tone === "green" ? "bg-emerald-50 text-emerald-500" : tone === "blue" ? "bg-blue-50 text-blue-500" : "bg-violet-50 text-violet-500"
                          }`}
                        >
                          <div className="h-4 w-4 rounded-md border border-current" />
                        </div>
                        <h4 className="mt-2.5 text-[15px] font-semibold tracking-[-0.04em] text-slate-950">{title}</h4>
                        <p className="mt-1 text-[11px] leading-4.5 text-slate-500">{desc}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 rounded-[18px] border border-slate-100 bg-white px-4 py-3.5 shadow-[0_16px_28px_rgba(15,23,42,0.05)]">
                    <div className="flex items-center justify-between">
                      <h4 className="text-[19px] font-semibold tracking-[-0.04em] text-slate-950">最近活动</h4>
                      <a className="text-[12px] font-medium text-blue-500" href="#">查看全部</a>
                    </div>
                    <div className="mt-2.5 space-y-2">
                      {[
                        ["产品策略圆桌讨论", "对话", "刚刚"],
                        ["Q2 目标与 OKR 规划", "文档", "1 小时前"],
                        ["市场活动流程图", "画布", "昨天"],
                        ["客户需求整理（草稿）", "草稿", "2 天前"],
                      ].map(([title, tag, time]) => (
                        <div key={title} className="grid grid-cols-[1fr_auto_auto] items-center gap-2.5 rounded-[14px] border border-slate-100 px-3 py-2">
                          <div>
                            <div className="text-[13px] font-medium text-slate-900">{title}</div>
                            <div className="mt-0.5 text-[11px] text-slate-400">{time}</div>
                          </div>
                          <span className="rounded-full bg-slate-50 px-2.5 py-1 text-[11px] text-slate-500">{tag}</span>
                          <div className="flex -space-x-2">
                            {[0, 1, 2].map((i) => (
                              <div key={i} className="h-5.5 w-5.5 rounded-full border-2 border-white bg-slate-200" />
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="flex min-h-0 items-center justify-center pl-3 pr-1">
            <div className="w-full max-w-[500px] rounded-[28px] border border-white/85 bg-white/93 px-11 pb-7 pt-8 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur-sm">
              <div className="flex items-center justify-center gap-4">
                <BrandMark className="h-[36px] w-[36px]" />
                <span className="text-[32px] font-semibold tracking-[-0.08em] text-slate-950">Eko</span>
              </div>

              <div className="mt-5 text-center">
                <h2 className="text-[36px] font-semibold tracking-[-0.07em] text-slate-950">欢迎回来</h2>
                <p className="mt-1.5 text-[15px] text-slate-500">登录你的 Eko 工作区</p>
              </div>

              <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
                <label className="block">
                  <span className="mb-1.5 block text-[13px] font-medium text-slate-500">邮箱</span>
                  <div className="flex h-[52px] items-center gap-2.5 rounded-[14px] border border-slate-200 px-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                    <svg viewBox="0 0 24 24" className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M4 7.2A2.2 2.2 0 0 1 6.2 5h11.6A2.2 2.2 0 0 1 20 7.2v9.6a2.2 2.2 0 0 1-2.2 2.2H6.2A2.2 2.2 0 0 1 4 16.8V7.2Z" />
                      <path d="m5.2 7 6.1 5.2a1 1 0 0 0 1.4 0L18.8 7" />
                    </svg>
                    <input
                      type="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="you@company.com"
                      className="w-full bg-transparent text-[15px] text-slate-900 outline-none placeholder:text-slate-400"
                    />
                  </div>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-[13px] font-medium text-slate-500">密码</span>
                  <div className="flex h-[52px] items-center gap-2.5 rounded-[14px] border border-slate-200 px-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                    <svg viewBox="0 0 24 24" className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M7.8 10.1V7.9a4.2 4.2 0 1 1 8.4 0v2.2" />
                      <rect x="5" y="10.1" width="14" height="10.9" rx="2.6" />
                    </svg>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="输入密码"
                      className="w-full bg-transparent text-[15px] text-slate-900 outline-none placeholder:text-slate-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((current) => !current)}
                      className="text-slate-400 transition hover:text-slate-500"
                    >
                      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                        <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z" />
                        <circle cx="12" cy="12" r="2.8" />
                      </svg>
                    </button>
                  </div>
                </label>

                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-3 text-[13px] text-slate-500">
                    <button
                      type="button"
                      onClick={() => setRemember((current) => !current)}
                      className={`flex h-6 w-6 items-center justify-center rounded-md border transition ${
                        remember ? "border-blue-500 bg-blue-500 text-white" : "border-slate-300 bg-white text-transparent"
                      }`}
                    >
                      <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="m3.5 8 2.5 2.5L12.5 4" />
                      </svg>
                    </button>
                    保持登录状态
                  </label>
                  <Link href="/login/forgot-password" className="text-[13px] font-semibold text-blue-500 hover:text-blue-600">
                    忘记密码？
                  </Link>
                </div>

                {error ? (
                  <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-[12px] text-rose-600">{error}</p>
                ) : null}

                <button
                  type="submit"
                  disabled={loginDisabled}
                  className="mt-2 h-[54px] w-full rounded-[14px] bg-gradient-to-r from-blue-500 to-blue-600 text-[18px] font-semibold text-white shadow-[0_14px_28px_rgba(37,99,235,0.2)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting ? "登录中..." : "登录"}
                </button>
              </form>

              <div className="mt-6 flex items-center gap-4 text-[12px] text-slate-400">
                <div className="h-px flex-1 bg-slate-200" />
                或使用以下方式继续
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              <div className="mt-4 space-y-3">
                <button className="flex h-[50px] w-full items-center justify-center gap-3 rounded-[14px] border border-slate-200 bg-white text-[15px] font-medium text-slate-900 shadow-[0_8px_20px_rgba(15,23,42,0.05)] transition hover:border-slate-300">
                  <FeishuLogo className="h-7 w-7" />
                  使用飞书继续
                </button>
                <button className="flex h-[50px] w-full items-center justify-center gap-3 rounded-[14px] border border-slate-200 bg-white text-[15px] font-medium text-slate-900 shadow-[0_8px_20px_rgba(15,23,42,0.05)] transition hover:border-slate-300">
                  <GoogleLogo className="h-7 w-7" />
                  使用 Google 继续
                </button>
              </div>

              <div className="mt-5 text-center text-[14px] text-slate-500">
                还没有账号？
                {" "}
                <a href="#" className="font-semibold text-blue-500 hover:text-blue-600">
                  立即创建
                </a>
              </div>

              <div className="mt-5 flex items-center justify-center gap-2.5 text-[12px] text-slate-400">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M12 3.5 5.8 6.1v5c0 4.2 2.4 7.9 6.2 9.4 3.8-1.5 6.2-5.2 6.2-9.4v-5L12 3.5Z" />
                  <path d="m9.7 12.1 1.6 1.7 3.4-3.9" />
                </svg>
                企业级安全保障。你的数据不会被用于训练 AI 模型。
              </div>
            </div>
          </section>
        </div>

        <footer className="pointer-events-none absolute bottom-[22px] left-1/2 flex w-[min(1280px,calc(100%-112px))] -translate-x-1/2 items-center justify-between text-[11px] text-slate-400">
          <span>© {currentYear} Eko Technologies Inc.</span>
          <div className="pointer-events-auto flex items-center gap-5">
            <a href="#">条款</a>
            <a href="#">隐私</a>
            <a href="#">安全</a>
            <a href="#">信任中心</a>
            <span>简体中文</span>
          </div>
        </footer>
      </div>
    </main>
  );
}
