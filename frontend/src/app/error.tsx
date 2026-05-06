"use client";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_50%_18%,#f8fbff_0%,#edf4ff_42%,#edf2fb_100%)] px-6 py-8 text-slate-900">
      <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-[1440px] items-center justify-center">
        <section className="w-full max-w-[520px] rounded-[30px] border border-white/80 bg-white/90 p-8 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur">
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-rose-100 bg-rose-50 text-rose-600">
            !
          </div>
          <h1 className="text-[24px] font-semibold tracking-[-0.04em] text-slate-950">页面暂时没有加载成功</h1>
          <p className="mt-3 text-[14px] leading-7 text-slate-500">
            Eko 已捕获这次前端异常。你可以先点击重试；如果仍然失败，请保留终端中的报错信息。
          </p>
          {error?.message ? (
            <pre className="mt-4 max-h-28 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3 text-left text-[12px] leading-5 text-slate-500">
              {error.message}
            </pre>
          ) : null}
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={reset}
              className="h-11 rounded-2xl bg-blue-600 px-5 text-[14px] font-semibold text-white shadow-[0_12px_28px_rgba(37,99,235,0.22)] transition hover:bg-blue-700"
            >
              重新加载
            </button>
            <a
              href="/login"
              className="inline-flex h-11 items-center rounded-2xl border border-slate-200 bg-white px-5 text-[14px] font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              回到登录页
            </a>
          </div>
        </section>
      </div>
    </main>
  );
}
