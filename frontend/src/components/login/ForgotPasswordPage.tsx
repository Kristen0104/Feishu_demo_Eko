"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

const PASSWORD_KEY = "eko:mock-password";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("sarah.chen@eko.ai");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showSuccess, setShowSuccess] = useState(false);
  const [error, setError] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password.trim() || !confirmPassword.trim()) {
      setError("请完整填写邮箱与新密码信息。");
      return;
    }

    if (password !== confirmPassword) {
      setError("两次输入的密码不一致，请重新确认。");
      return;
    }

    if (typeof window !== "undefined") {
      window.localStorage.setItem(PASSWORD_KEY, password);
    }

    setShowSuccess(true);
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_0%_0%,#eef5ff_0%,#f6f9ff_42%,#f4f7ff_100%)] px-4 pb-5 pt-6 text-slate-900 sm:px-7 sm:pt-8">
      <div className="mx-auto flex min-h-[calc(100vh-48px)] max-w-[1180px] items-center justify-center">
        <div className="w-full max-w-[620px] rounded-[32px] border border-white/80 bg-white/92 p-8 shadow-[0_28px_70px_rgba(15,23,42,0.11)] backdrop-blur-sm sm:p-10">
          <div className="mb-8 flex items-center justify-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-blue-600 text-xl font-bold text-white">e</div>
            <span className="text-[41px] font-semibold tracking-[-0.04em] text-slate-950">Eko</span>
          </div>

          {showSuccess ? (
            <div className="text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-3xl text-emerald-600">✓</div>
              <h1 className="mt-6 text-[38px] font-semibold tracking-[-0.05em] text-slate-950">更新密码成功</h1>
              <p className="mt-3 text-[16px] leading-7 text-slate-500">
                你的密码已经更新完成，现在可以返回登录页继续进入 Eko 工作区。
              </p>
              <div className="mt-8 flex justify-center">
                <Link
                  href="/login"
                  className="inline-flex h-[52px] items-center justify-center rounded-2xl bg-gradient-to-r from-blue-500 to-blue-600 px-8 text-[17px] font-semibold text-white shadow-[0_12px_24px_rgba(37,99,235,0.24)] transition hover:brightness-105"
                >
                  返回登录
                </Link>
              </div>
            </div>
          ) : (
            <>
              <div className="text-center">
                <h1 className="text-[42px] font-semibold tracking-[-0.05em] text-slate-950">重设密码</h1>
                <p className="mt-2 text-[20px] text-slate-500">为你的 Eko 工作区设置新的登录密码</p>
              </div>

              <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-500">邮箱</span>
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-[15px] outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:ring-3 focus:ring-blue-100"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-500">新密码</span>
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="请输入新密码"
                    className="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-[15px] outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:ring-3 focus:ring-blue-100"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-slate-500">确认新密码</span>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="请再次输入新密码"
                    className="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-[15px] outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:ring-3 focus:ring-blue-100"
                  />
                </label>

                {error ? <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] text-rose-600">{error}</p> : null}

                <button
                  type="submit"
                  className="h-[52px] w-full rounded-2xl bg-gradient-to-r from-blue-500 to-blue-600 text-[18px] font-semibold text-white shadow-[0_12px_24px_rgba(37,99,235,0.24)] transition hover:brightness-105"
                >
                  更新密码
                </button>
              </form>

              <div className="mt-6 text-center text-sm text-slate-500">
                想起密码了？
                {" "}
                <Link href="/login" className="font-semibold text-blue-500 hover:text-blue-600">
                  返回登录
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
