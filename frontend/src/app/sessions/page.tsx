import type { Metadata } from "next";
import Link from "next/link";

import { sessionListItems } from "@/lib/mock/session-list-data";

export const metadata: Metadata = {
  title: "会话列表 · Eko",
  description: "Eko Dashboard · 会话列表（Mock）",
};

const intentStyles = {
  chat: "border-emerald-500/35 bg-emerald-500/10 text-emerald-200",
  word: "border-sky-500/35 bg-sky-500/10 text-sky-200",
  canvas: "border-violet-500/35 bg-violet-500/10 text-violet-200",
};

export default function SessionsListPage() {
  return (
    <div className="min-h-screen bg-slate-950 pb-16 pt-10">
      <div className="mx-auto max-w-4xl px-5">
        <header className="mb-10 flex flex-col gap-4 border-b border-white/10 pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-500">
              Dashboard
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">
              会话列表
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400">
              对应 PRD「卡片跳转独立工作台」：从列表进入会话详情，查看 Word / 画布分支与 Mock
              Agent 状态。
            </p>
          </div>
          <Link
            href="/login"
            className="shrink-0 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-white/10"
          >
            切换账号
          </Link>
        </header>

        <ul className="flex flex-col gap-4">
          {sessionListItems.map((item) => (
            <li key={item.id}>
              <Link
                href={`/sessions/${encodeURIComponent(item.id)}`}
                className="group block rounded-2xl border border-white/10 bg-white/[0.03] p-5 transition hover:border-white/20 hover:bg-white/[0.06]"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${intentStyles[item.intent]}`}
                      >
                        {item.intentLabel}
                      </span>
                      <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        {item.updatedAtLabel}
                      </span>
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-white transition group-hover:text-sky-100">
                        {item.title}
                      </h2>
                      <p className="mt-2 text-sm leading-relaxed text-slate-400">
                        {item.summary}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300">
                      {item.stateLabel}
                    </span>
                    <span className="text-sm font-medium text-sky-400 transition group-hover:text-sky-300">
                      打开工作台 →
                    </span>
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
