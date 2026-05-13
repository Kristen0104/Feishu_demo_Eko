"use client";

export default function SessionDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-dvh bg-[radial-gradient(circle_at_top,_rgba(210,224,255,0.55),_rgba(246,248,252,1)_32%,_rgba(238,243,255,1)_100%)] px-3 py-4 sm:px-6 sm:py-8">
      <div className="mx-auto flex min-h-[calc(100dvh-32px)] max-w-[960px] items-center justify-center sm:min-h-[calc(100vh-64px)]">
        <div className="w-full rounded-[22px] border border-slate-200 bg-white p-5 text-center shadow-[0_18px_60px_rgba(100,116,139,0.14)] sm:rounded-[32px] sm:p-10">
          <p className="text-[12px] font-semibold uppercase tracking-[0.24em] text-slate-400 sm:text-[13px] sm:tracking-[0.3em]">Session Detail</p>
          <h1 className="mt-4 text-[24px] font-semibold tracking-[-0.04em] text-slate-950 sm:text-[32px] sm:tracking-[-0.05em]">会话详情加载失败</h1>
          <p className="mt-4 text-[15px] leading-7 text-slate-500">页面数据会优先使用本地 mock 兜底，你可以重新加载继续查看。</p>
          <p className="mt-3 break-words text-[12px] text-slate-400">{error.message}</p>
          <button
            type="button"
            onClick={() => reset()}
            className="mt-8 inline-flex h-11 w-full items-center justify-center rounded-[14px] bg-blue-600 px-6 text-[15px] font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.24)] sm:w-auto"
          >
            重新加载
          </button>
        </div>
      </div>
    </div>
  );
}
