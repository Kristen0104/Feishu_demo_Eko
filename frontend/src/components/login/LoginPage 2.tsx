"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

const MOCK_EMAIL = "sarah.chen@eko.ai";
const DEFAULT_PASSWORD = "eko123456";
const PASSWORD_KEY = "eko:mock-password";
const LAST_LOGIN_KEY = "eko:last-login-email";

const highlights = [
  {
    title: "把聊天转成可执行结果",
    description: "将想法、讨论和决策，自动转化为任务、计划、跟进项与落地建议。",
    tone: "emerald" as const,
  },
  {
    title: "AI 驱动的文稿与画布路由",
    description: "自动识别内容类型，智能分发到文稿、画布和回复等合适输出形式。",
    tone: "sky" as const,
  },
  {
    title: "面向团队的上下文同步",
    description: "连接工具与知识库，保持信息一致，让团队协作始终基于正确上下文。",
    tone: "violet" as const,
  },
];

function getCurrentMockPassword() {
  if (typeof window === "undefined") {
    return DEFAULT_PASSWORD;
  }
  return window.localStorage.getItem(PASSWORD_KEY) ?? DEFAULT_PASSWORD;
}

function BrandMark() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="ekoMarkLogin" x1="8" y1="8" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2E7BFF" />
          <stop offset="1" stopColor="#0F5CF4" />
        </linearGradient>
      </defs>
      <rect x="1.6" y="1.6" width="44.8" height="44.8" rx="16" fill="url(#ekoMarkLogin)" />
      <path
        d="M12.6 23.9C15.4 18.2 20.3 14.8 27 14.8C30.8 14.8 34.1 15.8 37 17.8L34.5 22C32.3 20.6 29.9 19.8 27 19.8C22.7 19.8 19.7 21.7 18 25.4H28.3V29.8H16.9C18.4 33.9 21.8 36.1 26.8 36.1C29.9 36.1 32.4 35.2 34.5 33.5L36.9 37.2C34.2 39.8 30.7 41.2 26.4 41.2C17.8 41.2 11.9 34.8 11.9 25.8C11.9 25.1 12.1 24.4 12.6 23.9Z"
        fill="white"
      />
    </svg>
  );
}

function FloatingIcon({ tone, children, className }: { tone: "emerald" | "sky" | "violet"; children: React.ReactNode; className: string }) {
  const styles =
    tone === "emerald"
      ? "border-emerald-100 bg-white text-emerald-500 shadow-[0_20px_40px_rgba(16,185,129,0.13)]"
      : tone === "sky"
        ? "border-blue-100 bg-white text-blue-500 shadow-[0_20px_40px_rgba(59,130,246,0.13)]"
        : "border-violet-100 bg-white text-violet-500 shadow-[0_20px_40px_rgba(139,92,246,0.13)]";

  return (
    <div className={`pointer-events-none absolute hidden h-16 w-16 items-center justify-center rounded-[22px] border backdrop-blur-sm lg:flex ${styles} ${className}`}>
      {children}
    </div>
  );
}

function FeatureIcon({ tone }: { tone: (typeof highlights)[number]["tone"] }) {
  const shell =
    tone === "emerald"
      ? "border-emerald-200 bg-emerald-50 text-emerald-600"
      : tone === "sky"
        ? "border-blue-200 bg-blue-50 text-blue-600"
        : "border-violet-200 bg-violet-50 text-violet-600";

  return (
    <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-[18px] border ${shell}`}>
      {tone === "emerald" ? (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <rect x="2.75" y="3.4" width="16.5" height="11.8" rx="3.4" stroke="currentColor" strokeWidth="1.55" />
          <path d="M7.2 15.1L6.3 18L9.6 15.1" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M7.3 8.4H14.7M7.3 11.2H12.8" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
        </svg>
      ) : tone === "sky" ? (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <path d="M5.8 2.8H12.7L16.8 6.8V18H5.8V2.8Z" stroke="currentColor" strokeWidth="1.55" strokeLinejoin="round" />
          <path d="M12.5 2.8V7H16.7" stroke="currentColor" strokeWidth="1.55" strokeLinejoin="round" />
          <path d="M8 10.1H13.9M8 12.9H13.9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
      ) : (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <circle cx="7.4" cy="7.6" r="2.5" stroke="currentColor" strokeWidth="1.45" />
          <circle cx="14.7" cy="6.8" r="2.15" stroke="currentColor" strokeWidth="1.45" />
          <path d="M4.2 16.8C4.7 14.4 6.4 13.1 8.8 13.1C11.1 13.1 12.8 14.4 13.3 16.8" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
          <path d="M13.2 16.2C13.5 14.7 14.6 13.8 16 13.8C17.5 13.8 18.7 14.7 19 16.2" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
        </svg>
      )}
    </span>
  );
}

function FeishuLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M3.1 6.2C3.1 5.1 4.2 4.4 5.2 4.8L9.4 6.4C10.4 6.8 10.7 8.1 10.1 8.9L7.5 12.3C6.9 13.1 5.7 13.1 5.1 12.3L3.4 9.9C3.2 9.6 3.1 9.3 3.1 8.9V6.2Z" fill="#10B981" />
      <path d="M10 2.7C10.4 1.8 11.6 1.6 12.3 2.3L16.7 6.6C17.4 7.3 17.1 8.5 16.2 8.9L11.9 10.6C10.9 11 9.9 10.3 9.9 9.2V3.8C9.9 3.4 9.9 3 10 2.7Z" fill="#3B82F6" />
      <path d="M12.2 11.2C12.6 10.3 13.8 10 14.5 10.7L17.2 13.3C17.9 14 17.7 15.2 16.8 15.7L11.8 18.1C10.8 18.6 9.7 17.9 9.7 16.8V13.2C9.7 12.7 10 12.2 10.4 12L12.2 11.2Z" fill="#2563EB" />
    </svg>
  );
}

function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M16.36 9.2C16.36 8.58 16.31 8.13 16.2 7.67H9.18V10.44H13.3C13.21 11.13 12.73 12.16 11.66 12.86L11.64 12.95L13.88 14.67L14.03 14.69C15.49 13.37 16.36 11.43 16.36 9.2Z" fill="#4285F4" />
      <path d="M9.18 16.42C11.2 16.42 12.89 15.77 14.03 14.69L11.66 12.86C11.02 13.29 10.17 13.59 9.18 13.59C7.2 13.59 5.51 12.27 4.91 10.45L4.83 10.46L2.5 12.25L2.47 12.33C3.61 14.56 6.16 16.42 9.18 16.42Z" fill="#34A853" />
      <path d="M4.91 10.45C4.75 9.99 4.66 9.49 4.66 8.97C4.66 8.45 4.75 7.95 4.9 7.49L4.89 7.39L2.53 5.57L2.46 5.6C1.99 6.53 1.72 7.58 1.72 8.97C1.72 10.36 1.99 11.41 2.46 12.33L4.91 10.45Z" fill="#FBBC05" />
      <path d="M9.18 4.35C10.43 4.35 11.27 4.88 11.75 5.33L14.08 3.12C12.88 2.03 11.2 1.52 9.18 1.52C6.16 1.52 3.61 3.38 2.46 5.6L4.9 7.49C5.51 5.67 7.2 4.35 9.18 4.35Z" fill="#EA4335" />
    </svg>
  );
}

export function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = useMemo(() => email.trim().length > 0 && password.trim().length > 0, [email, password]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    await new Promise((resolve) => setTimeout(resolve, 420));

    const currentPassword = getCurrentMockPassword();

    if (email.trim().toLowerCase() === MOCK_EMAIL && password === currentPassword) {
      if (remember) {
        window.localStorage.setItem(LAST_LOGIN_KEY, MOCK_EMAIL);
      } else {
        window.localStorage.removeItem(LAST_LOGIN_KEY);
      }
      router.push("/sessions");
      return;
    }

    setSubmitting(false);
    setError("账号或密码不正确，请检查后重新输入。");
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_12%_16%,#edf4ff_0%,#f6f9ff_40%,#f7f9fe_100%)] px-5 pb-5 pt-7 text-slate-900 sm:px-8 lg:px-10 lg:pt-8">
      <div className="pointer-events-none absolute left-[8%] top-[22%] hidden h-[620px] w-[620px] rounded-full border border-white/60 bg-[radial-gradient(circle,rgba(96,165,250,0.08),transparent_68%)] blur-[2px] lg:block" />
      <div className="pointer-events-none absolute left-[16%] top-[31%] hidden h-[460px] w-[460px] rounded-full border border-white/50 bg-[radial-gradient(circle,rgba(191,219,254,0.18),transparent_74%)] lg:block" />
      <div className="pointer-events-none absolute left-[24%] top-[40%] hidden h-[300px] w-[300px] rounded-full border border-white/45 bg-[radial-gradient(circle,rgba(147,197,253,0.14),transparent_76%)] lg:block" />
      <div className="pointer-events-none absolute left-[29%] top-[43%] hidden h-[220px] w-[220px] rounded-full border border-white/40 bg-[radial-gradient(circle,rgba(59,130,246,0.05),transparent_80%)] lg:block" />

      <FloatingIcon tone="emerald" className="left-[49%] top-[29%]">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <rect x="4" y="5" width="20" height="14" rx="5" stroke="currentColor" strokeWidth="1.9" />
          <path d="M9.5 13H18.5M9.5 9.7H16.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M10.5 19.1L9.1 22.3L12.7 19.1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </FloatingIcon>
      <FloatingIcon tone="sky" className="left-[46%] top-[49%]">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <path d="M8.1 4.8H16.6L21.4 9.4V23.1H8.1V4.8Z" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round" />
          <path d="M16.4 4.8V9.6H21.2" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round" />
          <path d="M10.6 13.2H17.9M10.6 16.8H17.9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </FloatingIcon>
      <FloatingIcon tone="violet" className="left-[45%] top-[67%]">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <circle cx="10.2" cy="10.1" r="3" stroke="currentColor" strokeWidth="1.8" />
          <circle cx="18.3" cy="9.1" r="2.6" stroke="currentColor" strokeWidth="1.8" />
          <path d="M6.7 21C7.3 18.2 9.2 16.7 12 16.7C14.7 16.7 16.7 18.2 17.3 21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M16.7 20.2C17.1 18.5 18.4 17.5 20 17.5C21.7 17.5 23 18.5 23.4 20.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </FloatingIcon>

      <div className="mx-auto flex min-h-[calc(100vh-52px)] w-full max-w-[1460px] flex-col justify-between gap-7 lg:grid lg:grid-cols-[minmax(0,0.92fr)_540px] lg:gap-12">
        <section className="relative flex min-w-0 flex-col justify-between pt-2">
          <div>
            <div className="mb-7 flex items-center gap-3">
              <BrandMark />
              <div className="flex items-center gap-4">
                <span className="text-[30px] font-semibold tracking-[-0.05em] text-slate-950">Eko</span>
                <span className="h-7 w-px bg-slate-200" />
                <span className="text-[15px] font-medium tracking-[-0.025em] text-slate-400">AI Workplace</span>
                <span className="rounded-xl border border-blue-100 bg-blue-50 px-3 py-1 text-[12px] font-semibold text-blue-600">AI 工作空间</span>
              </div>
            </div>

            <div className="max-w-[640px]">
              <h1 className="text-[44px] font-semibold leading-[1.14] tracking-[-0.055em] text-slate-950 xl:text-[58px]">
                AI，让对话快速转化为工作产出
              </h1>
              <p className="mt-4 max-w-[630px] text-[17px] leading-8 text-slate-600">
                将聊天或 IM 输入自动路由为聊天、文稿和画布输出，帮助团队更高效协作。
              </p>
            </div>

            <ul className="mt-8 max-w-[620px] space-y-5">
              {highlights.map((item) => (
                <li key={item.title} className="flex items-start gap-4">
                  <FeatureIcon tone={item.tone} />
                  <div className="max-w-[470px]">
                    <h2 className="text-[18px] font-semibold tracking-[-0.02em] text-slate-900">{item.title}</h2>
                    <p className="mt-1.5 text-[15px] leading-7 text-slate-600">{item.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-10 max-w-[650px] overflow-hidden rounded-[28px] border border-white/80 bg-white/88 shadow-[0_22px_56px_rgba(15,23,42,0.08)] backdrop-blur-sm">
            <div className="grid grid-cols-[190px_minmax(0,1fr)]">
              <div className="border-r border-slate-200/80 bg-[#fbfcff] p-5">
                <div className="mb-5 flex items-center gap-2 text-[15px] font-semibold tracking-[-0.03em] text-slate-900">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-[11px] bg-blue-600 text-sm font-bold text-white">e</span>
                  Eko
                </div>
                <div className="space-y-2 text-[13px]">
                  {["首页", "对话", "文档", "画布", "任务", "知识库", "团队", "设置"].map((item, index) => (
                    <div
                      key={item}
                      className={`flex items-center gap-2 rounded-xl px-3 py-2 ${index === 0 ? "bg-blue-50 font-semibold text-blue-600" : "text-slate-600"}`}
                    >
                      <span className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-current/10" />
                      {item}
                    </div>
                  ))}
                </div>
                <div className="mt-6 flex items-center gap-2 rounded-2xl border border-slate-200/80 bg-white px-3 py-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-[12px] font-semibold text-slate-700">SC</div>
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-semibold text-slate-900">Sarah Chen</p>
                    <p className="truncate text-[11px] text-slate-500">产品经理</p>
                  </div>
                </div>
              </div>

              <div className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-[23px] font-semibold tracking-[-0.04em] text-slate-900">早上好，欢迎回来 👋</h3>
                    <p className="mt-1 text-[12px] text-slate-500">有什么新想法？问问 Eko，或从以下快捷方式开始。</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">◌</span>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-slate-700">SC</div>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-3 gap-3">
                  {[
                    ["新建对话", "与 AI 互动和沟通", "emerald"],
                    ["新建文档", "创建文档型知识沉淀", "blue"],
                    ["新建画布", "可视化梳理思路流程", "violet"],
                  ].map(([title, desc, tone]) => (
                    <div key={title} className="rounded-2xl border border-slate-200/80 bg-white p-3.5 shadow-[0_6px_16px_rgba(15,23,42,0.04)]">
                      <div className={`mb-2 inline-flex h-9 w-9 items-center justify-center rounded-xl ${tone === "emerald" ? "bg-emerald-50 text-emerald-600" : tone === "blue" ? "bg-blue-50 text-blue-600" : "bg-violet-50 text-violet-600"}`}>
                        {tone === "emerald" ? "✦" : tone === "blue" ? "◫" : "▣"}
                      </div>
                      <p className="text-[14px] font-semibold text-slate-900">{title}</p>
                      <p className="mt-1 text-[11px] leading-5 text-slate-500">{desc}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-5 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_6px_16px_rgba(15,23,42,0.04)]">
                  <div className="flex items-center justify-between">
                    <h4 className="text-[14px] font-semibold text-slate-900">最近活动</h4>
                    <button type="button" className="text-[11px] font-medium text-blue-600">
                      查看全部
                    </button>
                  </div>
                  <div className="mt-3 space-y-2.5">
                    {[
                      ["产品策略圆桌讨论", "对话", "刚刚"],
                      ["Q2 目标与 OKR 规划", "文档", "1 小时前"],
                      ["市场活动流程图", "画布", "昨天"],
                      ["客户需求整理（草稿）", "草稿", "2 天前"],
                    ].map(([title, tag, time]) => (
                      <div key={title} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50/75 px-3 py-2">
                        <p className="truncate text-[12px] font-medium text-slate-800">{title}</p>
                        <div className="flex items-center gap-2">
                          <span className="rounded-full bg-white px-2 py-0.5 text-[10px] text-slate-500 ring-1 ring-slate-200">{tag}</span>
                          <span className="whitespace-nowrap text-[10px] text-slate-400">{time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[540px] lg:ml-auto lg:mr-0 lg:w-[540px] lg:self-center">
          <div className="rounded-[36px] border border-white/85 bg-white/94 px-10 py-9 shadow-[0_30px_74px_rgba(15,23,42,0.12)] backdrop-blur-sm">
            <div className="mb-6 flex items-center justify-center gap-3">
              <BrandMark />
              <span className="text-[30px] font-semibold tracking-[-0.045em] text-slate-950">Eko</span>
            </div>

            <div className="text-center">
              <h2 className="text-[34px] font-semibold tracking-[-0.05em] text-slate-950">欢迎回来</h2>
              <p className="mt-1.5 text-[17px] text-slate-500">登录你的 Eko 工作区</p>
            </div>

            <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-500">邮箱</span>
                <div className="relative">
                  <svg className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                    <rect x="2.4" y="3.5" width="13.2" height="10.6" rx="2.4" stroke="currentColor" strokeWidth="1.35" />
                    <path d="M3.4 4.7L9 9.4L14.6 4.7" stroke="currentColor" strokeWidth="1.35" strokeLinejoin="round" />
                  </svg>
                  <input
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="h-[58px] w-full rounded-[18px] border border-slate-200 bg-white pl-12 pr-4 text-[16px] outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                  />
                </div>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-slate-500">密码</span>
                <div className="relative">
                  <svg className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                    <rect x="3.4" y="8.1" width="11.2" height="7.1" rx="2.1" stroke="currentColor" strokeWidth="1.35" />
                    <path d="M5.8 8V6.3C5.8 4.55 7.15 3.2 9 3.2C10.85 3.2 12.2 4.55 12.2 6.3V8" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
                  </svg>
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="输入密码"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-[58px] w-full rounded-[18px] border border-slate-200 bg-white pl-12 pr-12 text-[16px] outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-600"
                    aria-label={showPassword ? "隐藏密码" : "显示密码"}
                  >
                    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                      <path d="M1.8 9C3.2 6.3 5.7 4.6 9 4.6C12.3 4.6 14.8 6.3 16.2 9C14.8 11.7 12.3 13.4 9 13.4C5.7 13.4 3.2 11.7 1.8 9Z" stroke="currentColor" strokeWidth="1.25" />
                      <circle cx="9" cy="9" r="2.1" stroke="currentColor" strokeWidth="1.25" />
                    </svg>
                  </button>
                </div>
              </label>

              <div className="flex items-center justify-between pt-0.5 text-[14px]">
                <label className="inline-flex items-center gap-2.5 text-slate-500">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(event) => setRemember(event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  保持登录状态
                </label>
                <Link href="/login/forgot-password" className="font-medium text-blue-500 hover:text-blue-600">
                  忘记密码？
                </Link>
              </div>

              {error ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] text-rose-600">{error}</p> : null}

              <button
                type="submit"
                disabled={!canSubmit || submitting}
                className="mt-1 h-[58px] w-full rounded-[18px] bg-gradient-to-r from-[#2e7bff] to-[#155df5] text-[24px] font-semibold tracking-[-0.03em] text-white shadow-[0_16px_28px_rgba(37,99,235,0.24)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "登录中…" : "登录"}
              </button>
            </form>

            <div className="my-7 flex items-center gap-3 text-[13px] text-slate-400">
              <span className="h-px flex-1 bg-slate-200" />
              <span>或使用以下方式继续</span>
              <span className="h-px flex-1 bg-slate-200" />
            </div>

            <div className="space-y-3">
              <button type="button" className="flex h-[56px] w-full items-center justify-center gap-3 rounded-[18px] border border-slate-200 bg-white text-[17px] font-medium text-slate-700 transition hover:bg-slate-50">
                <FeishuLogo />
                使用飞书继续
              </button>
              <button type="button" className="flex h-[56px] w-full items-center justify-center gap-3 rounded-[18px] border border-slate-200 bg-white text-[17px] font-medium text-slate-700 transition hover:bg-slate-50">
                <GoogleLogo />
                使用 Google 继续
              </button>
            </div>

            <p className="mt-6 text-center text-[15px] text-slate-500">
              还没有账号？
              {" "}
              <button type="button" className="font-semibold text-blue-500 hover:text-blue-600">
                立即创建
              </button>
            </p>

            <div className="mt-7 border-t border-slate-100 pt-4 text-center text-[12px] text-slate-400">
              企业级安全保障。你的数据不会被用于训练 AI 模型。
            </div>
          </div>
        </section>
      </div>

      <footer className="mx-auto mt-4 flex w-full max-w-[1460px] flex-wrap items-center justify-center gap-x-8 gap-y-2 text-[13px] text-slate-400">
        <span>© 2024 Eko Technologies Inc.</span>
        <span>条款</span>
        <span>隐私</span>
        <span>安全</span>
        <span>信任中心</span>
        <span>简体中文</span>
      </footer>
    </main>
  );
}
