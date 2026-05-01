"use client";

export default function SessionsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(210,224,255,0.55),_rgba(246,248,252,1)_32%,_rgba(238,243,255,1)_100%)] px-6 py-8">
      <div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-[960px] items-center justify-center">
        <div className="w-full rounded-[32px] border border-slate-200 bg-white p-10 text-center shadow-[0_18px_60px_rgba(100,116,139,0.14)]">
          <p className="text-[13px] font-semibold uppercase tracking-[0.3em] text-slate-400">Sessions</p>
          <h1 className="mt-4 text-[32px] font-semibold tracking-[-0.05em] text-slate-950">会话页暂时没有加载成功</h1>
          <p className="mt-4 text-[15px] leading-7 text-slate-500">
            已为你保留当前工作区结构。你可以重新加载页面，或稍后再试。
          </p>
          <p className="mt-3 text-[12px] text-slate-400">{error.message}</p>
          <button
            type="button"
            onClick={() => reset()}
            className="mt-8 inline-flex h-11 items-center justify-center rounded-[14px] bg-blue-600 px-6 text-[15px] font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.24)]"
          >
            重新加载
          </button>
        </div>
      </div>
    </div>
  );
}
