import Link from "next/link";

/** 首页不再自动跳转，避免影响调试和页面恢复 */
export default function RootPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-3xl space-y-6">
        <h1 className="text-3xl font-semibold">Eko 页面入口</h1>
        <p className="text-slate-400">已关闭自动 redirect，点击下面链接进入目标页面。</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Link className="rounded-xl border border-white/15 bg-white/5 px-4 py-3 hover:bg-white/10" href="/login">
            /login
          </Link>
          <Link className="rounded-xl border border-white/15 bg-white/5 px-4 py-3 hover:bg-white/10" href="/sessions">
            /sessions
          </Link>
          <Link
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-3 hover:bg-white/10"
            href="/sessions/meeting-confirmation"
          >
            /sessions/meeting-confirmation
          </Link>
          <Link
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-3 hover:bg-white/10"
            href="/sessions/weekly-marketing-summary"
          >
            /sessions/weekly-marketing-summary
          </Link>
          <Link
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-3 hover:bg-white/10 sm:col-span-2"
            href="/sessions/q2-ads-review"
          >
            /sessions/q2-ads-review
          </Link>
        </div>
      </div>
    </main>
  );
}
