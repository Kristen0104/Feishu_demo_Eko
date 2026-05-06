"use client";

import Link from "next/link";

export function ForgotPasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_12%_16%,#edf4ff_0%,#f6f9ff_40%,#f7f9fe_100%)] px-6 py-10 text-slate-900">
      <section className="w-full max-w-[560px] rounded-[28px] border border-white/85 bg-white/95 p-8 shadow-[0_24px_70px_rgba(15,23,42,0.1)]">
        <h1 className="text-[36px] font-semibold tracking-[-0.05em] text-slate-950">重设密码</h1>
        <p className="mt-3 text-[15px] leading-7 text-slate-600">
          当前版本先完成邮箱登录和注册，密码重设后续再接后端流程。你可以先返回登录页继续使用账号密码登录。
        </p>
        <div className="mt-8">
          <Link
            href="/login"
            className="inline-flex h-[52px] items-center justify-center rounded-2xl bg-gradient-to-r from-blue-500 to-blue-600 px-8 text-[16px] font-semibold text-white shadow-[0_12px_24px_rgba(37,99,235,0.24)] transition hover:brightness-105"
          >
            返回登录
          </Link>
        </div>
      </section>
    </main>
  );
}
