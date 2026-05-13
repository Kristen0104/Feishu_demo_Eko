"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { EkoSquircleMark, FeishuLogo } from "@/components/login/brand-icons";
import { apiUrl } from "@/lib/eko-api";
import { saveAccessToken } from "@/lib/auth-token";
import { useAppStore } from "@/store/app-store";
import { useProfileStore } from "@/store/profile-store";

const MOCK_LOGIN = {
  email: "demo@eko.local",
  password: "Eko123456",
  token: "mock-demo-access-token",
};

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
    <div className={`flex h-16 w-16 items-center justify-center rounded-[20px] border lg:h-12 lg:w-12 lg:rounded-[16px] ${tones[tone]}`}>
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
    green: "border-emerald-200/70 text-emerald-500 shadow-[0_12px_24px_rgba(16,185,129,0.13),inset_0_1px_0_rgba(255,255,255,0.85),inset_0_-10px_20px_rgba(16,185,129,0.05)]",
    blue: "border-blue-200/70 text-blue-500 shadow-[0_12px_24px_rgba(37,99,235,0.13),inset_0_1px_0_rgba(255,255,255,0.85),inset_0_-10px_20px_rgba(37,99,235,0.05)]",
    purple: "border-violet-200/70 text-violet-500 shadow-[0_12px_24px_rgba(139,92,246,0.13),inset_0_1px_0_rgba(255,255,255,0.85),inset_0_-10px_20px_rgba(139,92,246,0.05)]",
  };

  return (
    <div
      className={`pointer-events-none absolute z-20 flex items-center justify-center border bg-white/[0.08] backdrop-blur-[2px] ${tones[tone]} ${className}`}
    >
      {children}
    </div>
  );
}

export function LoginPage({ justRegistered = false }: { justRegistered?: boolean }) {
  const router = useRouter();
  const setLogin = useAppStore((state) => state.setLogin);
  const adoptProfileOwner = useProfileStore((state) => state.adoptProfileOwner);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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

    try {
      if (trimmedEmail === MOCK_LOGIN.email && password === MOCK_LOGIN.password) {
        saveAccessToken(MOCK_LOGIN.token, remember);
        adoptProfileOwner(trimmedEmail);
        setLogin(trimmedEmail, { remember });
        router.push("/home");
        return;
      }

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
      adoptProfileOwner(trimmedEmail);
      setLogin(trimmedEmail, { remember });
      router.push("/home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
    <main className="relative h-dvh overflow-hidden bg-[linear-gradient(160deg,#EEF6FF_0%,#F8FBFF_54%,#EDF5FF_100%)] text-slate-900 lg:hidden">
      <div className="pointer-events-none absolute -left-20 top-10 h-64 w-64 rounded-full bg-blue-200/25 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 top-[420px] h-72 w-72 rounded-full bg-blue-300/20 blur-3xl" />
      <div className="pointer-events-none absolute right-[-108px] top-[150px] h-[360px] w-[360px] rounded-full border border-white/55" />
      <div className="pointer-events-none absolute right-[-68px] top-[190px] h-[280px] w-[280px] rounded-full border border-white/45" />
      <div className="pointer-events-none absolute right-[-28px] top-[230px] h-[200px] w-[200px] rounded-full border border-white/35" />
      <span className="pointer-events-none absolute right-6 top-[294px] h-2.5 w-2.5 rounded-full bg-white/90 shadow-[0_0_20px_rgba(255,255,255,0.8)]" />
      <span className="pointer-events-none absolute bottom-20 right-7 h-3 w-3 rounded-full bg-white/90 shadow-[0_0_20px_rgba(255,255,255,0.8)]" />

      <div className="relative z-10 mx-auto flex h-dvh w-full max-w-[390px] origin-top flex-col overflow-hidden px-4 pb-3 pt-4 min-[390px]:px-5 min-[390px]:pb-4 min-[390px]:pt-5 [@media(max-height:700px)]:scale-[0.92]">
        <nav className="flex items-center justify-between">
          <Link href="/login" className="flex items-center gap-3" aria-label="Eko 登录页">
            <EkoSquircleMark className="h-6 w-6 min-[390px]:h-7 min-[390px]:w-7" />
            <span className="text-[20px] font-bold tracking-[-0.06em] text-slate-950 min-[390px]:text-[22px]">Eko</span>
          </Link>
          <span className="inline-flex h-6 items-center rounded-full border border-blue-200/80 bg-white/55 px-2.5 text-[12px] font-semibold text-blue-600 shadow-[0_10px_24px_rgba(37,99,235,0.08)] backdrop-blur-sm min-[390px]:h-7 min-[390px]:px-3 min-[390px]:text-[13px]">
            AI 工作空间
          </span>
        </nav>

        <section className="relative mt-4 min-[390px]:mt-5">
          <h1 className="whitespace-nowrap text-[clamp(19px,5.6vw,23px)] font-extrabold leading-[1.1] tracking-[-0.04em] text-[#0B1020]">
            AI，让对话快速转化为工作产出
          </h1>

          <FloatingIcon className="right-[-6px] top-8 h-9 w-9 rounded-[15px] min-[390px]:right-[-4px] min-[390px]:h-10 min-[390px]:w-10 min-[390px]:rounded-[16px]" tone="green">
            <svg viewBox="0 0 24 24" className="h-4 w-4 min-[390px]:h-[18px] min-[390px]:w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.9">
              <path d="M8 9.5h8" />
              <path d="M8 13.5h4.2" />
              <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
            </svg>
          </FloatingIcon>
          <FloatingIcon className="right-[-7px] top-[102px] h-9 w-9 rounded-[15px] min-[390px]:right-[-5px] min-[390px]:top-[108px] min-[390px]:h-10 min-[390px]:w-10 min-[390px]:rounded-[16px]" tone="blue">
            <svg viewBox="0 0 24 24" className="h-4 w-4 min-[390px]:h-[18px] min-[390px]:w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.9">
              <path d="M8 3.5h6.3L19.5 8v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6.5 20v-15A1.5 1.5 0 0 1 8 3.5Z" />
              <path d="M14 3.8V8h4.2" />
              <path d="M9.2 12.2h5.9" />
              <path d="M9.2 16h5.9" />
            </svg>
          </FloatingIcon>

          <div className="mt-3 space-y-1.5 text-[11.5px] leading-[18px] text-slate-500 min-[390px]:mt-3.5 min-[390px]:space-y-2 min-[390px]:text-[12.5px] min-[390px]:leading-5">
            <p className="flex items-start gap-2.5">
              <svg viewBox="0 0 24 24" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#7890AD] min-[390px]:h-4 min-[390px]:w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M8 9.5h8" />
                <path d="M8 13.5h4.2" />
                <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
              </svg>
              <span>将聊天自动路由为文稿、任务或画布并输出</span>
            </p>
            <p className="flex items-start gap-2.5">
              <svg viewBox="0 0 24 24" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#7890AD] min-[390px]:h-4 min-[390px]:w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
                <circle cx="8.2" cy="9.2" r="2.9" />
                <circle cx="15.9" cy="9.2" r="2.9" />
              </svg>
              <span>打通团队协作，让信息在工作流中顺畅流转</span>
            </p>
            <p className="flex items-start gap-2.5">
              <svg viewBox="0 0 24 24" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#7890AD] min-[390px]:h-4 min-[390px]:w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M12 3.2 13.3 8l4.7 1.4-4.7 1.4L12 15.6l-1.3-4.8L6 9.4 10.7 8 12 3.2Z" />
                <path d="m5 15 1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1L5 15Z" />
              </svg>
              <span>AI 驱动，帮你从想法到成果更快一步</span>
            </p>
          </div>
        </section>

        <section className="relative mx-auto mt-3 w-full max-w-[342px] rounded-[24px] border border-white/55 bg-white/78 px-4 pb-3 pt-4 shadow-[0_18px_52px_rgba(82,122,180,0.12),0_2px_10px_rgba(255,255,255,0.42)_inset] backdrop-blur-[22px] before:pointer-events-none before:absolute before:inset-x-3 before:-inset-y-3 before:-z-10 before:rounded-[30px] before:bg-[radial-gradient(circle_at_50%_12%,rgba(255,255,255,0.66),rgba(255,255,255,0.22)_42%,rgba(96,165,250,0.10)_72%,rgba(96,165,250,0)_100%)] before:blur-2xl min-[390px]:mt-4 min-[390px]:rounded-[26px] min-[390px]:px-5 min-[390px]:pb-4 min-[390px]:pt-5">
          <FloatingIcon className="left-[-13px] top-[-18px] h-9 w-9 rounded-[15px] min-[390px]:left-[-16px] min-[390px]:top-[-20px] min-[390px]:h-10 min-[390px]:w-10 min-[390px]:rounded-[16px]" tone="purple">
            <svg viewBox="0 0 24 24" className="h-4 w-4 min-[390px]:h-[18px] min-[390px]:w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.9">
              <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
              <circle cx="8.2" cy="9.2" r="2.9" />
              <circle cx="15.9" cy="9.2" r="2.9" />
            </svg>
          </FloatingIcon>

          <div className="flex items-center justify-center gap-2.5">
            <EkoSquircleMark className="h-5 w-5 min-[390px]:h-6 min-[390px]:w-6" />
            <span className="text-[19px] font-bold tracking-[-0.06em] text-slate-950 min-[390px]:text-[21px]">Eko</span>
          </div>
          <div className="mt-2.5 text-center min-[390px]:mt-3">
            <h2 className="text-[22px] font-extrabold tracking-[-0.05em] text-[#0B1020] min-[390px]:text-[24px]">欢迎回来</h2>
            <p className="mt-0.5 text-[12px] text-[#7085A3] min-[390px]:text-[13px]">登录你的 Eko 工作区</p>
          </div>

          {justRegistered ? (
            <p className="mt-5 rounded-2xl border border-emerald-200/90 bg-emerald-50/90 px-4 py-3 text-center text-[12px] font-medium text-emerald-800">
              注册已完成，请使用刚创建的账号继续登录。
            </p>
          ) : null}

          <form className="mt-3 space-y-2.5 min-[390px]:mt-3.5 min-[390px]:space-y-3" noValidate onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-1 block text-[11px] font-semibold text-[#526680] min-[390px]:text-[12px]">邮箱</span>
              <div className="flex h-9 items-center gap-2.5 rounded-[12px] border border-[#D8E2EF] bg-white/70 px-3 min-[390px]:h-10">
                <svg viewBox="0 0 24 24" className="h-4 w-4 text-[#8EA0B8]" fill="none" stroke="currentColor" strokeWidth="1.8">
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
                  className="w-full bg-transparent text-[14px] text-slate-900 outline-none placeholder:text-[#94A3B8]"
                />
              </div>
            </label>

            <label className="block">
              <span className="mb-1 block text-[11px] font-semibold text-[#526680] min-[390px]:text-[12px]">密码</span>
              <div className="flex h-9 items-center gap-2.5 rounded-[12px] border border-[#D8E2EF] bg-white/70 px-3 min-[390px]:h-10">
                <svg viewBox="0 0 24 24" className="h-4 w-4 text-[#8EA0B8]" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M7.8 10.1V7.9a4.2 4.2 0 1 1 8.4 0v2.2" />
                  <rect x="5" y="10.1" width="14" height="10.9" rx="2.6" />
                </svg>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="输入密码"
                  className="w-full bg-transparent text-[14px] text-slate-900 outline-none placeholder:text-[#94A3B8]"
                />
                <button type="button" onClick={() => setShowPassword((current) => !current)} className="text-[#8EA0B8] transition hover:text-slate-500" aria-label={showPassword ? "隐藏密码" : "显示密码"}>
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z" />
                    <circle cx="12" cy="12" r="2.8" />
                  </svg>
                </button>
              </div>
            </label>

            <div className="flex items-center justify-between gap-3 text-[12px] min-[390px]:text-[13px]">
              <label className="flex cursor-pointer select-none items-center gap-2 text-[#64748B]">
                <input type="checkbox" name="remember" checked={remember} onChange={(event) => setRemember(event.target.checked)} className="peer sr-only" />
                <span
                  aria-hidden
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2 ${
                    remember ? "border-blue-500 bg-blue-500 text-white" : "border-[#D8E2EF] bg-white text-transparent"
                  }`}
                >
                  <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="m3.5 8 2.5 2.5L12.5 4" />
                  </svg>
                </span>
                <span className="whitespace-nowrap">保持登录状态</span>
              </label>
              <Link href="/login/forgot-password" className="font-semibold text-blue-600">
                忘记密码？
              </Link>
            </div>

            {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-[12px] text-rose-600">{error}</p> : null}

            <button
              type="submit"
              disabled={loginDisabled}
              className="h-10 w-full rounded-[12px] bg-gradient-to-r from-[#2F80FF] to-[#2563EB] text-[15px] font-bold text-white shadow-[0_12px_24px_rgba(37,99,235,0.20)] transition hover:brightness-105 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60 min-[390px]:h-11 min-[390px]:text-[16px]"
            >
              {submitting ? "登录中..." : "登录"}
            </button>
          </form>

          <div className="mt-3 flex items-center gap-2.5 text-[11px] text-[#8EA0B8] min-[390px]:mt-3.5 min-[390px]:text-[12px]">
            <div className="h-px flex-1 bg-[#DCE5F0]" />
            使用企业身份继续
            <div className="h-px flex-1 bg-[#DCE5F0]" />
          </div>

          <Link href="/login/feishu/start" className="mt-2 flex h-9 w-full items-center justify-center gap-2.5 rounded-[12px] border border-[#D8E2EF] bg-white text-[13px] font-semibold text-slate-800 shadow-[0_8px_18px_rgba(15,23,42,0.04)] min-[390px]:mt-2.5 min-[390px]:h-10 min-[390px]:text-[14px]">
            <FeishuLogo className="h-5 w-5 min-[390px]:h-6 min-[390px]:w-6" />
            使用飞书登录
          </Link>

          <div className="mt-2.5 text-center text-[12px] text-[#7085A3] min-[390px]:mt-3 min-[390px]:text-[13px]">
            还没有账号？
            {" "}
            <Link href="/login/register" className="font-semibold text-blue-600">
              立即创建
            </Link>
          </div>

          <div className="mt-2 flex items-start justify-center gap-1.5 text-[10px] leading-[14px] text-[#8A9BB3] min-[390px]:mt-2.5 min-[390px]:text-[10.5px] min-[390px]:leading-4">
            <svg viewBox="0 0 24 24" className="mt-px h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M12 3.5 5.8 6.1v5c0 4.2 2.4 7.9 6.2 9.4 3.8-1.5 6.2-5.2 6.2-9.4v-5L12 3.5Z" />
              <path d="m9.7 12.1 1.6 1.7 3.4-3.9" />
            </svg>
            <span>企业级安全保障，你的数据不会被用于训练 AI 模型。</span>
          </div>
        </section>

        <footer className="mt-2 text-center text-[10.5px] text-[#7F93AE] min-[390px]:mt-3 min-[390px]:text-[11px]">
          © {currentYear} Eko Technologies Inc.
        </footer>
      </div>
    </main>

    <main className="relative hidden min-h-screen overflow-y-auto bg-[radial-gradient(circle_at_50%_18%,#f8fbff_0%,#edf4ff_42%,#edf2fb_100%)] px-4 pb-6 pt-4 text-slate-900 sm:px-6 lg:block lg:min-h-dvh lg:overflow-x-hidden lg:overflow-y-auto lg:px-6 lg:pb-6 lg:pt-2">
      <div className="relative mx-auto flex w-full max-w-[1400px] flex-col lg:justify-start">
        {/* 水波纹 + 悬浮图标（全页背景层，对齐前一版位置） */}
        <div className="pointer-events-none absolute inset-0 z-0 hidden overflow-hidden lg:block">
          <div className="absolute left-[46%] top-[50%] -translate-x-1/2 -translate-y-1/2">
            <div className="absolute left-1/2 top-1/2 h-[560px] w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/45 bg-[radial-gradient(circle_at_center,rgba(191,219,254,0.22)_0%,rgba(191,219,254,0.08)_28%,rgba(255,255,255,0)_72%)] shadow-[0_0_140px_rgba(96,165,250,0.14)]" />
            <div className="absolute left-1/2 top-1/2 h-[480px] w-[480px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/50 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.34)_0%,rgba(255,255,255,0.06)_52%,rgba(255,255,255,0)_100%)]" />
            <div className="absolute left-1/2 top-1/2 h-[400px] w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/55" />
            <div className="absolute left-1/2 top-1/2 h-[320px] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/40" />
            <div className="absolute left-1/2 top-1/2 h-[248px] w-[248px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/35 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.2)_0%,rgba(255,255,255,0)_70%)]" />
            <div className="absolute left-1/2 top-1/2 h-[176px] w-[176px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-100/40" />
          </div>

          <FloatingIcon className="absolute left-[52%] top-[28%] hidden h-[58px] w-[58px] rounded-[20px] lg:flex" tone="green">
            <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
              <path d="M8 9.5h8" />
              <path d="M8 13.5h4.2" />
              <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
            </svg>
          </FloatingIcon>

          <FloatingIcon className="absolute left-[45%] top-[44%] hidden h-[58px] w-[58px] rounded-[20px] lg:flex" tone="blue">
            <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
              <path d="M8 3.5h6.3L19.5 8v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6.5 20v-15A1.5 1.5 0 0 1 8 3.5Z" />
              <path d="M14 3.8V8h4.2" />
              <path d="M9.2 12.2h5.9" />
              <path d="M9.2 16h5.9" />
            </svg>
          </FloatingIcon>

          <FloatingIcon className="absolute left-[56%] top-[58%] hidden h-[58px] w-[58px] rounded-[20px] lg:flex" tone="purple">
            <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9">
              <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
              <circle cx="8.2" cy="9.2" r="2.9" />
              <circle cx="15.9" cy="9.2" r="2.9" />
            </svg>
          </FloatingIcon>
        </div>

        {/* 顶栏品牌区：不参与缩放，避免放大缩小时被裁切或遮挡 */}
        <div className="relative z-30 w-full shrink-0 overflow-visible px-0 lg:px-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 lg:gap-x-3 lg:gap-y-1.5">
            <div className="flex items-center gap-4 lg:gap-2.5">
              <EkoSquircleMark className="h-[34px] w-[34px] sm:h-[38px] sm:w-[38px] lg:h-8 lg:w-8" />
              <span className="text-[30px] font-semibold tracking-[-0.08em] text-slate-950 sm:text-[35px] lg:text-[24px]">Eko</span>
            </div>
            <div className="h-7 w-px bg-slate-200 lg:h-5" />
            <span className="text-[18px] font-medium tracking-[-0.04em] text-slate-400 sm:text-[20px] lg:text-[15px]">AI Workplace</span>
            <span className="inline-flex h-8 shrink-0 items-center rounded-full border border-blue-100 bg-blue-50/85 px-3.5 text-[12px] font-medium text-blue-500 shadow-[0_8px_20px_rgba(59,130,246,0.10)] sm:text-[13px] lg:h-7 lg:px-3 lg:text-[11px]">
              AI 工作空间
            </span>
          </div>

          <h1 className="mt-4 w-full max-w-[calc(100vw-3rem)] overflow-visible text-[34px] font-semibold leading-[1.12] tracking-[-0.05em] text-slate-950 sm:mt-5 sm:text-[44px] lg:mt-3 lg:text-[clamp(18px,2.2vw,28px)] lg:leading-tight lg:whitespace-nowrap xl:max-w-none xl:text-[clamp(20px,2vw,30px)]">
            AI，让对话快速转化为工作产出
          </h1>
        </div>

        <div className="w-full lg:origin-top lg:zoom-[0.84] xl:zoom-[0.88]">
        <div className="relative grid grid-cols-1 items-start gap-x-[72px] gap-y-10 px-0 pb-16 pt-2 lg:grid-cols-[minmax(0,1fr)_460px] lg:items-center lg:gap-x-12 lg:gap-y-0 lg:px-4 lg:pb-0 lg:pt-1">
          <section className="relative z-10 flex min-h-0 flex-col justify-center pl-0 pr-0 lg:pl-2">
            <div className="relative z-10 max-w-[760px]">
              <p className="max-w-[620px] text-[14px] leading-[1.7] text-slate-500 sm:text-[15px] lg:max-w-[540px] lg:text-[13px] lg:leading-snug">
                将聊天或 IM 输入自动路由为聊天、文稿和画布输出，帮助团队更高效协作。
              </p>

              <div className="mt-5 space-y-3 sm:mt-6 sm:space-y-3.5 lg:mt-3 lg:space-y-2.5">
                <div className="flex items-start gap-4 lg:gap-3">
                  <FeatureIcon tone="green">
                    <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8 lg:h-6 lg:w-6" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M8 9.5h8" />
                      <path d="M8 13.5h4.2" />
                      <path d="M7.8 20 3.9 22v-5.2A8 8 0 0 1 4 4.8 9.6 9.6 0 0 1 12 2c5.6 0 10 4.1 10 9.2s-4.4 9.3-10 9.3c-1.4 0-2.8-.2-4.2-.6Z" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[16px] font-semibold tracking-[-0.03em] text-slate-950 sm:text-[17px] lg:text-[14px]">把聊天转成可执行结果</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500 lg:text-[11px] lg:leading-snug">
                      将想法、讨论和决策，自动转化为任务、计划、跟进项与落地建议。
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4 lg:gap-3">
                  <FeatureIcon tone="blue">
                    <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8 lg:h-6 lg:w-6" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M8 3.5h6.3L19.5 8v12a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6.5 20v-15A1.5 1.5 0 0 1 8 3.5Z" />
                      <path d="M14 3.8V8h4.2" />
                      <path d="M9.2 12.2h5.9" />
                      <path d="M9.2 16h5.9" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[16px] font-semibold tracking-[-0.03em] text-slate-950 sm:text-[17px] lg:text-[14px]">AI 驱动的文稿与画布路由</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500 lg:text-[11px] lg:leading-snug">
                      自动识别内容类型，智能分发到文稿、画布和回复等合适输出形式。
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-4 lg:gap-3">
                  <FeatureIcon tone="purple">
                    <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8 lg:h-6 lg:w-6" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M6.6 19.6c1.4-2.5 2.8-3.8 5.3-3.8s3.9 1.3 5.4 3.8" />
                      <circle cx="8.2" cy="9.2" r="2.9" />
                      <circle cx="15.9" cy="9.2" r="2.9" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[16px] font-semibold tracking-[-0.03em] text-slate-950 sm:text-[17px] lg:text-[14px]">面向团队的上下文同步</h2>
                    <p className="mt-1 max-w-[420px] text-[12px] leading-[1.6] text-slate-500 lg:text-[11px] lg:leading-snug">
                      连接工具与知识库，保持信息一致，让团队协作始终基于正确上下文。
                    </p>
                  </div>
                </div>
              </div>
            </div>


            <div className="relative z-10 mt-6 w-full max-w-[540px] rounded-[24px] border border-white/85 bg-white/88 shadow-[0_24px_64px_rgba(15,23,42,0.09)] backdrop-blur-md lg:mt-4 lg:origin-top-left lg:zoom-[0.88] xl:zoom-[0.84]">
              <div className="grid grid-cols-[154px_1fr]">
                <aside className="border-r border-slate-100 px-4.5 py-5">
                  <div className="flex items-center gap-3">
                    <EkoSquircleMark className="h-7 w-7" />
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

          <section className="relative z-10 flex min-h-0 items-start justify-center pl-0 pr-0 lg:items-center lg:pl-3 lg:pr-1">
            <div className="w-full max-w-[500px] rounded-[28px] border border-white/85 bg-white/93 px-6 pb-6 pt-7 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur-sm sm:px-8 sm:pb-7 sm:pt-8 lg:max-w-[440px] lg:rounded-[24px] lg:px-8 lg:pb-5 lg:pt-5 lg:shadow-[0_18px_56px_rgba(15,23,42,0.10)]">
              <div className="flex items-center justify-center gap-4 lg:gap-2.5">
                <EkoSquircleMark className="h-[32px] w-[32px] sm:h-[36px] sm:w-[36px] lg:h-8 lg:w-8" />
                <span className="text-[28px] font-semibold tracking-[-0.08em] text-slate-950 sm:text-[32px] lg:text-[24px]">Eko</span>
              </div>

              <div className="mt-5 text-center lg:mt-3">
                <h2 className="text-[30px] font-semibold tracking-[-0.07em] text-slate-950 sm:text-[36px] lg:text-[26px]">欢迎回来</h2>
                <p className="mt-1.5 text-[14px] text-slate-500 sm:text-[15px] lg:mt-1 lg:text-[13px]">登录你的 Eko 工作区</p>
              </div>

              {justRegistered ? (
                <p className="mt-4 rounded-2xl border border-emerald-200/90 bg-emerald-50/90 px-4 py-3 text-center text-[12px] font-medium text-emerald-800">
                  注册已完成，请使用刚创建的账号继续登录。
                </p>
              ) : null}

              <form className="mt-6 space-y-4 lg:mt-4 lg:space-y-3" noValidate onSubmit={handleSubmit}>
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
                使用企业身份继续
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              <div className="mt-4">
                <Link
                  href="/login/feishu/start"
                  className="flex h-[50px] w-full items-center justify-center gap-3 rounded-[14px] border border-slate-200 bg-white text-[15px] font-medium text-slate-700 shadow-[0_8px_20px_rgba(15,23,42,0.05)] transition hover:border-blue-200 hover:text-blue-600"
                >
                  <FeishuLogo className="h-7 w-7" />
                  使用飞书登录
                </Link>
              </div>

              <div className="mt-5 text-center text-[14px] text-slate-500">
                还没有账号？
                {" "}
                <Link
                  href="/login/register"
                  className="font-semibold text-blue-500 transition hover:text-blue-600"
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

        <footer className="pointer-events-none relative mt-8 flex w-full shrink-0 items-center justify-between text-[11px] text-slate-400 lg:mt-1 lg:mb-0 lg:pb-1 lg:text-[10px]">
          <span>© {currentYear} Eko Technologies Inc.</span>
          <div className="pointer-events-auto flex items-center gap-5 lg:gap-4">
            <a href="#">条款</a>
            <a href="#">隐私</a>
            <a href="#">安全</a>
            <a href="#">信任中心</a>
            <span>简体中文</span>
          </div>
        </footer>
        </div>
      </div>
    </main>
    </>
  );
}
