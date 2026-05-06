"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { BrandMark, FeishuLogo, GoogleLogo } from "@/components/login/brand-icons";
import { apiUrl } from "@/lib/eko-api";
import { saveAccessToken } from "@/lib/auth-token";
import {
  EKO_MOCK_ACCESS_TOKEN,
  EKO_MOCK_EMAIL,
  EKO_MOCK_PASSWORD,
  isMockLoginEnabled,
  matchesMockCredentials,
} from "@/lib/mock-login";
import { useAppStore } from "@/store/app-store";

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

export function LoginPage({ justRegistered = false }: { justRegistered?: boolean }) {
  const router = useRouter();
  const setLogin = useAppStore((state) => state.setLogin);
  /** 默认填入演示凭证（界面不展示）；避免「登录」因空字段一直处于 disabled */
  const [email, setEmail] = useState(() => (isMockLoginEnabled() ? EKO_MOCK_EMAIL : ""));
  const [password, setPassword] = useState(() => (isMockLoginEnabled() ? EKO_MOCK_PASSWORD : ""));
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const currentYear = new Date().getFullYear();

  const loginDisabled = useMemo(
    () => !email.trim() || !password.trim() || submitting,
    [email, password, submitting],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail || !password.trim()) {
      setSubmitting(false);
      setError("请输入邮箱和密码。");
      return;
    }

    if (isMockLoginEnabled() && matchesMockCredentials(trimmedEmail, password)) {
      saveAccessToken(EKO_MOCK_ACCESS_TOKEN, remember);
      setLogin(trimmedEmail, { remember });
      router.push("/home");
      setSubmitting(false);
      return;
    }

    try {
      const res = await fetch(apiUrl("/api/v1/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmedEmail,
          password,
        }),
      });
      const json = (await res.json()) as {
        code?: number;
        message?: string;
        detail?: string;
        data?: { access_token?: string };
      };
      if (!res.ok || json.code !== 0 || !json.data?.access_token) {
        throw new Error(json.message || json.detail || res.statusText || "登录失败");
      }
      saveAccessToken(json.data.access_token, remember);
      setLogin(trimmedEmail, { remember });
      router.push("/home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-y-auto bg-[radial-gradient(circle_at_50%_18%,#f8fbff_0%,#edf4ff_42%,#edf2fb_100%)] px-4 pb-6 pt-4 text-slate-900 sm:px-6 lg:px-6">
      <div className="mx-auto flex min-h-[calc(100vh-6px)] w-full max-w-[1400px] flex-col">
        <div className="grid flex-1 grid-cols-1 items-start gap-x-[72px] gap-y-10 px-0 pb-16 pt-2 lg:grid-cols-[minmax(0,1fr)_500px] lg:items-center lg:px-4 lg:pb-20 lg:pt-3">
          <section className="relative flex min-h-0 flex-col justify-center pl-0 pr-0 lg:pl-2">
            <div className="relative z-10 max-w-[760px]">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-4">
                  <BrandMark className="h-[34px] w-[34px] sm:h-[38px] sm:w-[38px]" />
                  <span className="text-[30px] font-semibold tracking-[-0.08em] text-slate-950 sm:text-[35px]">Eko</span>
                </div>
                <div className="h-7 w-px bg-slate-200" />
                <span className="text-[18px] font-medium tracking-[-0.04em] text-slate-400 sm:text-[20px]">AI Workplace</span>
                <span className="inline-flex h-8 items-center rounded-full border border-blue-100 bg-blue-50/85 px-3.5 text-[12px] font-medium text-blue-500 shadow-[0_8px_20px_rgba(59,130,246,0.10)] sm:text-[13px]">
                  AI 工作空间
                </span>
              </div>

              <div className="mt-5 sm:mt-6">
                <h1 className="max-w-[760px] text-[26px] font-semibold leading-[1.15] tracking-[-0.05em] text-slate-950 sm:text-[32px] xl:text-[36px]">
                  AI，让对话快速转化为工作产出
                </h1>
                <p className="mt-3 max-w-[620px] text-[14px] leading-[1.7] text-slate-500 sm:text-[15px]">
                  将聊天或 IM 输入自动路由为聊天、文稿和画布输出，帮助团队更高效协作。
                </p>
              </div>

              <div className="mt-5 space-y-3 sm:mt-6 sm:space-y-3.5">
                <div className="flex items-start gap-4">
                  <FeatureIcon tone="green">
                    <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M8 9.5h8" />
                      <path d="M8 13.5h4.2" />
                      <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[16px] font-semibold tracking-[-0.03em] text-slate-950 sm:text-[17px]">把聊天转成可执行结果</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500">
                      将想法、讨论和决策，自动转化为任务、计划、跟进项与落地建议。
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <FeatureIcon tone="blue">
                    <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M8 3.5h6.3L19.5 8v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6.5 20v-15A1.5 1.5 0 0 1 8 3.5Z" />
                      <path d="M14 3.8V8h4.2" />
                      <path d="M9.2 12.2h5.9" />
                      <path d="M9.2 16h5.9" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[16px] font-semibold tracking-[-0.03em] text-slate-950 sm:text-[17px]">AI 驱动的文稿与画布路由</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500">
                      自动识别内容类型，智能分发到文稿、画布和回复等合适输出形式。
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <FeatureIcon tone="purple">
                    <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
                      <circle cx="8.2" cy="9.2" r="2.9" />
                      <circle cx="15.9" cy="9.2" r="2.9" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[16px] font-semibold tracking-[-0.03em] text-slate-950 sm:text-[17px]">面向团队的上下文同步</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500">
                      连接工具与知识库，保持信息一致，让团队协作始终基于正确上下文。
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="absolute left-[204px] top-[246px] hidden h-[360px] w-[360px] rounded-full border border-white/40 bg-[radial-gradient(circle_at_center,rgba(191,219,254,0.28)_0%,rgba(191,219,254,0.12)_26%,rgba(255,255,255,0)_72%)] shadow-[0_0_120px_rgba(96,165,250,0.12)] xl:block" />
            <div className="absolute left-[236px] top-[280px] hidden h-[300px] w-[300px] rounded-full border border-white/40 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.4)_0%,rgba(255,255,255,0.08)_54%,rgba(255,255,255,0)_100%)] xl:block" />
            <div className="absolute left-[266px] top-[310px] hidden h-[246px] w-[246px] rounded-full border border-white/50 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.28)_0%,rgba(255,255,255,0.02)_70%)] xl:block" />

            <FloatingIcon className="left-[590px] top-[242px] hidden h-14 w-14 rounded-[22px] xl:flex" tone="green">
              <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
                <path d="M8 9.5h8" />
                <path d="M8 13.5h4.2" />
                <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
              </svg>
            </FloatingIcon>

            <FloatingIcon className="left-[518px] top-[458px] hidden h-14 w-14 rounded-[22px] xl:flex" tone="blue">
              <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
                <path d="M8 3.5h6.3L19.5 8v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6.5 20v-15A1.5 1.5 0 0 1 8 3.5Z" />
                <path d="M14 3.8V8h4.2" />
                <path d="M9.2 12.2h5.9" />
                <path d="M9.2 16h5.9" />
              </svg>
            </FloatingIcon>

            <FloatingIcon className="left-[608px] top-[612px] hidden h-14 w-14 rounded-[22px] xl:flex" tone="purple">
              <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
                <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
                <circle cx="8.2" cy="9.2" r="2.9" />
                <circle cx="15.9" cy="9.2" r="2.9" />
              </svg>
            </FloatingIcon>

            <div className="relative z-10 mt-6 w-full max-w-[540px] rounded-[24px] border border-white/85 bg-white/88 shadow-[0_24px_64px_rgba(15,23,42,0.09)] backdrop-blur-md lg:scale-[0.9] lg:origin-top-left xl:scale-[0.86]">
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

          <section className="relative z-20 flex min-h-0 items-start justify-center pl-0 pr-0 lg:items-center lg:pl-3 lg:pr-1">
            <div className="w-full max-w-[500px] rounded-[28px] border border-white/85 bg-white/93 px-6 pb-6 pt-7 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur-sm sm:px-8 sm:pb-7 sm:pt-8 lg:px-11">
              <div className="flex items-center justify-center gap-4">
                <BrandMark className="h-[32px] w-[32px] sm:h-[36px] sm:w-[36px]" />
                <span className="text-[28px] font-semibold tracking-[-0.08em] text-slate-950 sm:text-[32px]">Eko</span>
              </div>

              <div className="mt-5 text-center">
                <h2 className="text-[30px] font-semibold tracking-[-0.07em] text-slate-950 sm:text-[36px]">欢迎回来</h2>
                <p className="mt-1.5 text-[14px] text-slate-500 sm:text-[15px]">登录你的 Eko 工作区</p>
              </div>

              {justRegistered ? (
                <p className="mt-4 rounded-2xl border border-emerald-200/90 bg-emerald-50/90 px-4 py-3 text-center text-[12px] font-medium text-emerald-800">
                  注册已完成，请使用刚创建的账号继续登录。
                </p>
              ) : null}

              <form className="mt-6 space-y-4" noValidate onSubmit={handleSubmit}>
                <label className="block">
                  <span className="mb-1.5 block text-[13px] font-medium text-slate-500">邮箱</span>
                  <div className="flex h-[52px] items-center gap-2.5 rounded-[14px] border border-slate-200 px-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                    <svg viewBox="0 0 24 24" className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M4 7.2A2.2 2.2 0 0 1 6.2 5h11.6A2.2 2.2 0 0 1 20 7.2v9.6a2.2 2.2 0 0 1-2.2 2.2H6.2A2.2 2.2 0 0 1 4 16.8V7.2Z" />
                      <path d="m5.2 7 6.1 5.2a1 1 0 0 0 1.4 0L18.8 7" />
                    </svg>
                    <input
                      type="text"
                      inputMode="email"
                      autoCapitalize="none"
                      autoCorrect="off"
                      spellCheck={false}
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
                  <label
                    className="flex cursor-pointer select-none items-center gap-3 text-[13px] text-slate-500"
                    title="勾选：15 天内同一浏览器可免重复登录；不勾选：仅本次浏览有效，关闭标签后需重新输入"
                  >
                    <input
                      type="checkbox"
                      name="remember"
                      checked={remember}
                      onChange={(event) => setRemember(event.target.checked)}
                      className="peer sr-only"
                    />
                    <span
                      aria-hidden
                      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border transition peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2 ${
                        remember ? "border-blue-500 bg-blue-500 text-white" : "border-slate-300 bg-white text-transparent"
                      }`}
                    >
                      <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="m3.5 8 2.5 2.5L12.5 4" />
                      </svg>
                    </span>
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

              <div className="mt-5 flex items-center gap-4 text-[12px] text-slate-400 sm:mt-6">
                <div className="h-px flex-1 bg-slate-200" />
                或使用以下方式继续
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              <div className="mt-4 space-y-3">
                <Link
                  href="/login/feishu/start"
                  className="flex h-[50px] w-full items-center justify-center gap-3 rounded-[14px] border border-slate-200 bg-white text-[15px] font-medium text-slate-700 shadow-[0_8px_20px_rgba(15,23,42,0.05)] transition hover:border-blue-200 hover:text-blue-600"
                >
                  <FeishuLogo className="h-7 w-7" />
                  使用飞书登录
                </Link>
                <button
                  type="button"
                  disabled
                  className="flex h-[50px] w-full items-center justify-center gap-3 rounded-[14px] border border-slate-200 bg-white text-[15px] font-medium text-slate-400 shadow-[0_8px_20px_rgba(15,23,42,0.05)] opacity-60"
                  aria-disabled="true"
                >
                  <GoogleLogo className="h-7 w-7" />
                  Google 登录暂未接入
                </button>
              </div>

              <div className="mt-5 text-center text-[14px] text-slate-500">
                还没有账号？
                {" "}
                <Link
                  href="/login/register"
                  className="rounded-md font-semibold text-blue-500 outline outline-1 outline-blue-500/40 hover:text-blue-600"
                >
                  立即创建
                </Link>
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

        <footer className="pointer-events-none relative mt-8 flex w-full items-center justify-between text-[11px] text-slate-400 lg:absolute lg:bottom-[22px] lg:left-1/2 lg:w-[min(1280px,calc(100%-112px))] lg:-translate-x-1/2">
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
