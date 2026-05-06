"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";

import { BrandMark, FeishuLogo } from "@/components/login/brand-icons";
import { apiUrl } from "@/lib/eko-api";
import { saveAccessToken } from "@/lib/auth-token";
import { useAppStore } from "@/store/app-store";
import { useProfileStore } from "@/store/profile-store";

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
    <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] border ${tones[tone]}`}>{children}</div>
  );
}

export function CreateAccountPage() {
  const router = useRouter();
  const setLogin = useAppStore((state) => state.setLogin);
  const adoptProfileOwner = useProfileStore((state) => state.adoptProfileOwner);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const currentYear = new Date().getFullYear();

  const disabled = useMemo(() => {
    return (
      !fullName.trim() ||
      !email.trim() ||
      !password.trim() ||
      !confirmPassword.trim() ||
      !agreed ||
      submitting
    );
  }, [fullName, email, password, confirmPassword, agreed, submitting]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim().toLowerCase();

    if (!trimmedName) {
      setSubmitting(false);
      setError("请填写姓名。");
      return;
    }
    if (!trimmedEmail || !trimmedEmail.includes("@")) {
      setSubmitting(false);
      setError("请填写有效的工作邮箱。");
      return;
    }
    if (password.length < 8) {
      setSubmitting(false);
      setError("密码至少 8 位字符。");
      return;
    }
    if (password !== confirmPassword) {
      setSubmitting(false);
      setError("两次输入的密码不一致。");
      return;
    }
    if (!agreed) {
      setSubmitting(false);
      setError("请阅读并同意服务条款与隐私政策。");
      return;
    }

    void (async () => {
      try {
        const res = await fetch(apiUrl("/api/v1/auth/register"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            display_name: trimmedName,
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
          throw new Error(json.message || json.detail || res.statusText || "注册失败");
        }
        saveAccessToken(json.data.access_token, true);
        adoptProfileOwner(trimmedEmail);
        setLogin(trimmedEmail, { remember: true });
        router.push("/home");
      } catch (e) {
        setError(e instanceof Error ? e.message : "注册失败。");
      } finally {
        setSubmitting(false);
      }
    })();
  }

  return (
    <main className="relative min-h-screen bg-[radial-gradient(circle_at_50%_18%,#f8fbff_0%,#edf4ff_42%,#edf2fb_100%)] px-6 pb-6 pt-5 text-slate-900">
      <div className="mx-auto flex h-[calc(100vh-8px)] w-full max-w-[1400px] flex-col">
        <div className="grid min-h-0 flex-1 grid-cols-1 items-center gap-y-10 gap-x-[72px] px-4 pb-16 pt-3 lg:grid-cols-[minmax(520px,1fr)_500px]">
          <section className="relative order-2 flex min-h-0 flex-col justify-center pl-0 pr-0 lg:order-1 lg:pl-2">
            <div className="relative z-10 mx-auto w-full max-w-[640px] lg:mx-0">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-4">
                  <BrandMark className="h-[38px] w-[38px]" />
                  <span className="text-[35px] font-semibold tracking-[-0.08em] text-slate-950">Eko</span>
                </div>
                <div className="h-7 w-px bg-slate-200" />
                <span className="text-[20px] font-medium tracking-[-0.04em] text-slate-400">AI Workplace</span>
              </div>

              <h1 className="mt-6 text-[40px] font-semibold leading-[1.12] tracking-[-0.05em] text-slate-950 lg:text-[48px]">
                创建你的 Eko 工作区
              </h1>
              <p className="mt-3 max-w-[520px] text-[15px] leading-[1.7] text-slate-500">
                与飞书团队类似，从注册到邀请成员、配置应用，只需几分钟。完成注册后，使用企业邮箱即可登录并邀请同事加入。
              </p>

              <div className="mt-8 space-y-4">
                <div className="flex items-start gap-4">
                  <FeatureIcon tone="green">
                    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M12 4.2v2.2M6.2 7.1h11.6" />
                      <path d="M7.2 7.1v10.2a1.2 1.2 0 0 0 1.2 1.2h7.2a1.2 1.2 0 0 0 1.2-1.2V7.1" />
                      <path d="M9.2 10.2h5.6M9.2 14.2h5.6" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">团队与工作空间一起就绪</h2>
                    <p className="mt-1 max-w-[440px] text-[13px] leading-[1.6] text-slate-500">
                      注册后即可创建空间、导入通讯录并与现有工具集成。
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <FeatureIcon tone="blue">
                    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M8 6h8v12H8z" />
                      <path d="M12 9v6M9 12h6" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">安全可控的企业账号体系</h2>
                    <p className="mt-1 max-w-[440px] text-[13px] leading-[1.6] text-slate-500">
                      支持域校验与 SSO 预留接口，当前注册流程已接入后端 JWT。
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <FeatureIcon tone="purple">
                    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <circle cx="12" cy="12" r="7.5" />
                      <path d="M12 8.5v3.2l2.2 1.2" />
                    </svg>
                  </FeatureIcon>
                  <div className="pt-1">
                    <h2 className="text-[17px] font-semibold tracking-[-0.03em] text-slate-950">按需启用 AI 能力</h2>
                    <p className="mt-1 max-w-[440px] text-[13px] leading-[1.6] text-slate-500">
                      对话、文稿与画布在同一工作区内编排，符合团队合规节奏。
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="pointer-events-none absolute left-[120px] top-[220px] hidden h-[280px] w-[280px] rounded-full border border-white/40 bg-[radial-gradient(circle_at_center,rgba(191,219,254,0.28)_0%,rgba(191,219,254,0.1)_50%,rgba(255,255,255,0)_70%)] shadow-[0_0_100px_rgba(96,165,250,0.1)] lg:block" />
          </section>

          <section className="order-1 flex min-h-0 items-center justify-center pl-1 pr-1 lg:order-2 lg:pl-3 lg:pr-1">
            <div className="w-full max-w-[500px] rounded-[28px] border border-white/85 bg-white/93 px-9 pb-7 pt-8 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur-sm sm:px-11">
              <div className="flex items-center justify-center gap-4">
                <BrandMark className="h-[36px] w-[36px]" />
                <span className="text-[32px] font-semibold tracking-[-0.08em] text-slate-950">Eko</span>
              </div>

              <div className="mt-5 text-center">
                <h2 className="text-[36px] font-semibold tracking-[-0.07em] text-slate-950">创建账号</h2>
                <p className="mt-1.5 text-[15px] text-slate-500">注册你的 Eko 工作区账号</p>
              </div>

              <form className="mt-6 space-y-4" noValidate onSubmit={handleSubmit}>
                <label className="block">
                  <span className="mb-1.5 block text-[13px] font-medium text-slate-500">姓名</span>
                  <div className="flex h-[52px] items-center gap-2.5 rounded-[14px] border border-slate-200 px-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <circle cx="12" cy="8.4" r="3.4" />
                      <path d="M6.5 19.2c.9-3 3.3-4.8 5.5-4.8s4.6 1.8 5.5 4.8" />
                    </svg>
                    <input
                      type="text"
                      autoComplete="name"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      placeholder="请输入姓名或昵称"
                      className="w-full bg-transparent text-[15px] text-slate-900 outline-none placeholder:text-slate-400"
                    />
                  </div>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-[13px] font-medium text-slate-500">工作邮箱</span>
                  <div className="flex h-[52px] items-center gap-2.5 rounded-[14px] border border-slate-200 px-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M4 7.2A2.2 2.2 0 0 1 6.2 5h11.6A2.2 2.2 0 0 1 20 7.2v9.6a2.2 2.2 0 0 1-2.2 2.2H6.2A2.2 2.2 0 0 1 4 16.8V7.2Z" />
                      <path d="m5.2 7 6.1 5.2a1 1 0 0 0 1.4 0L18.8 7" />
                    </svg>
                    <input
                      type="text"
                      inputMode="email"
                      autoComplete="email"
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
                    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M7.8 10.1V7.9a4.2 4.2 0 1 1 8.4 0v2.2" />
                      <rect x="5" y="10.1" width="14" height="10.9" rx="2.6" />
                    </svg>
                    <input
                      type={showPassword ? "text" : "password"}
                      autoComplete="new-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="至少 8 位字符"
                      className="w-full bg-transparent text-[15px] text-slate-900 outline-none placeholder:text-slate-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((current) => !current)}
                      className="text-slate-400 transition hover:text-slate-500"
                      aria-label={showPassword ? "隐藏密码" : "显示密码"}
                    >
                      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                        <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z" />
                        <circle cx="12" cy="12" r="2.8" />
                      </svg>
                    </button>
                  </div>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-[13px] font-medium text-slate-500">确认密码</span>
                  <div className="flex h-[52px] items-center gap-2.5 rounded-[14px] border border-slate-200 px-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M7.8 10.1V7.9a4.2 4.2 0 1 1 8.4 0v2.2" />
                      <rect x="5" y="10.1" width="14" height="10.9" rx="2.6" />
                    </svg>
                    <input
                      type={showConfirm ? "text" : "password"}
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      placeholder="再次输入密码"
                      className="w-full bg-transparent text-[15px] text-slate-900 outline-none placeholder:text-slate-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm((current) => !current)}
                      className="text-slate-400 transition hover:text-slate-500"
                      aria-label={showConfirm ? "隐藏密码" : "显示密码"}
                    >
                      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                        <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z" />
                        <circle cx="12" cy="12" r="2.8" />
                      </svg>
                    </button>
                  </div>
                </label>

                <label className="flex cursor-pointer select-none items-start gap-3 pt-1 text-[13px] leading-snug text-slate-500">
                  <input
                    type="checkbox"
                    name="terms"
                    checked={agreed}
                    onChange={(event) => setAgreed(event.target.checked)}
                    className="peer sr-only"
                  />
                  <span
                    aria-hidden
                    className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border transition peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2 ${
                      agreed ? "border-blue-500 bg-blue-500 text-white" : "border-slate-300 bg-white text-transparent"
                    }`}
                  >
                    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="m3.5 8 2.5 2.5L12.5 4" />
                    </svg>
                  </span>
                  <span>
                    我已阅读并同意
                    <a href="#" className="font-semibold text-blue-500 hover:text-blue-600">
                      《服务条款》
                    </a>
                    和
                    <a href="#" className="font-semibold text-blue-500 hover:text-blue-600">
                      《隐私政策》
                    </a>
                  </span>
                </label>

                {error ? (
                  <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-[12px] text-rose-600">{error}</p>
                ) : null}

                <button
                  type="submit"
                  disabled={disabled}
                  className="mt-2 h-[54px] w-full rounded-[14px] bg-gradient-to-r from-blue-500 to-blue-600 text-[18px] font-semibold text-white shadow-[0_14px_28px_rgba(37,99,235,0.2)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting ? "提交中..." : "创建账号"}
                </button>
              </form>

              <div className="mt-6 flex items-center gap-4 text-[12px] text-slate-400">
                <div className="h-px flex-1 bg-slate-200" />
                使用企业身份继续
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              <div className="mt-4">
                <a
                  href="/login/feishu/start"
                  className="flex h-[50px] w-full items-center justify-center gap-3 rounded-[14px] border border-slate-200 bg-white text-[15px] font-medium text-slate-700 shadow-[0_8px_20px_rgba(15,23,42,0.05)] transition hover:border-blue-200 hover:text-blue-600"
                >
                  <FeishuLogo className="h-7 w-7" />
                  使用飞书注册 / 登录
                </a>
              </div>

              <div className="mt-5 text-center text-[14px] text-slate-500">
                已有账号？
                {" "}
                <Link href="/login" className="font-semibold text-blue-500 transition hover:text-blue-600">
                  立即登录
                </Link>
              </div>

              <div className="mt-5 flex items-center justify-center gap-2.5 text-[12px] text-slate-400">
                <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8">
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
          <div className="pointer-events-auto hidden items-center gap-5 sm:flex">
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
