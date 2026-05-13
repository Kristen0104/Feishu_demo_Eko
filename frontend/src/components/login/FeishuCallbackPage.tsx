"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { EkoSquircleMark, FeishuLogo } from "@/components/login/brand-icons";
import { saveAccessToken } from "@/lib/auth-token";
import { clearFeishuLoginDraft, exchangeFeishuLogin, readFeishuLoginDraft } from "@/lib/feishu-auth";
import { useAppStore } from "@/store/app-store";
import { useProfileStore } from "@/store/profile-store";

type FeishuCallbackPageProps = {
  code: string | null;
  state: string | null;
  error: string | null;
  errorDescription: string | null;
};

export function FeishuCallbackPage({ code, state, error, errorDescription }: FeishuCallbackPageProps) {
  const router = useRouter();
  const setLogin = useAppStore((store) => store.setLogin);
  const adoptProfileOwner = useProfileStore((store) => store.adoptProfileOwner);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("正在完成飞书登录...");
  const callbackSummary = (() => {
    if (typeof window === "undefined") {
      return "无本地登录草稿";
    }
    const draft = readFeishuLoginDraft();
    return draft ? `state ${draft.state.slice(0, 6)}...` : "无本地登录草稿";
  })();

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (error) {
        setStatus("error");
        setMessage(errorDescription ? `${error}: ${errorDescription}` : error);
        clearFeishuLoginDraft();
        return;
      }

      if (!code || !state) {
        setStatus("error");
        setMessage("缺少飞书回调参数 code 或 state。");
        clearFeishuLoginDraft();
        return;
      }

      try {
        setStatus("loading");
        setMessage("正在向后端换取登录凭证...");
        const result = await exchangeFeishuLogin(code, state, readFeishuLoginDraft()?.redirectUri);
        if (cancelled) return;

        saveAccessToken(result.access_token, true);
        const loginLabel =
          result.user.email?.trim() ||
          result.user.display_name ||
          result.user.feishu_user_id ||
          result.user.user_id;
        adoptProfileOwner(result.user.email?.trim().toLowerCase() || null);
        setLogin(loginLabel, { remember: true });
        clearFeishuLoginDraft();
        setStatus("success");
        setMessage("登录成功，正在进入工作台...");
        router.replace("/home");
      } catch (e) {
        if (cancelled) return;
        clearFeishuLoginDraft();
        setStatus("error");
        setMessage(e instanceof Error ? e.message : "飞书登录失败。");
      }
    }

    void run();

    return () => {
      cancelled = true;
    };
  }, [adoptProfileOwner, code, error, errorDescription, router, setLogin, state]);

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_top,#eef5ff_0%,#edf2fb_38%,#e8eefb_100%)] px-4 py-8 text-slate-900">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(59,130,246,0.16)_0%,rgba(59,130,246,0)_30%),radial-gradient(circle_at_80%_30%,rgba(99,102,241,0.14)_0%,rgba(99,102,241,0)_28%),radial-gradient(circle_at_50%_85%,rgba(16,185,129,0.10)_0%,rgba(16,185,129,0)_30%)]" />

      <section className="relative w-full max-w-[520px] rounded-[28px] border border-white/90 bg-white/92 px-7 py-8 shadow-[0_30px_90px_rgba(15,23,42,0.12)] backdrop-blur-md sm:px-10">
        <div className="flex items-center justify-center gap-4">
          <EkoSquircleMark className="h-[38px] w-[38px]" />
          <span className="text-[32px] font-semibold tracking-[-0.08em] text-slate-950">Eko</span>
        </div>

        <div className="mt-7 flex flex-col items-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-[22px] border border-blue-100 bg-blue-50 text-blue-500 shadow-[0_18px_36px_rgba(37,99,235,0.10)]">
            <FeishuLogo className="h-8 w-8" />
          </div>
          <h1 className="mt-5 text-[34px] font-semibold tracking-[-0.06em] text-slate-950">
            {status === "success" ? "登录完成" : "正在完成飞书登录"}
          </h1>
          <p className="mt-2 max-w-[360px] text-[14px] leading-[1.7] text-slate-500">{message}</p>
          <div className="mt-4 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-[12px] text-slate-500" suppressHydrationWarning>
            {callbackSummary}
          </div>
        </div>

        {status === "error" ? (
          <div className="mt-6 rounded-[18px] border border-rose-200 bg-rose-50 px-4 py-3 text-[13px] leading-[1.6] text-rose-700">
            {message}
          </div>
        ) : (
          <div className="mt-6 rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-[13px] leading-[1.6] text-slate-600">
            如果页面没有自动跳转，请关闭这个窗口并返回 Eko。
          </div>
        )}
      </section>
    </main>
  );
}
