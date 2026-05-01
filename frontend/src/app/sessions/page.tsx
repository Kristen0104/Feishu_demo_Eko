import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "会话列表 · Eko",
  description: "Eko Dashboard · 会话总览（浅色版）",
};

const navItems = ["主页", "会话", "文档", "画布", "Agents", "设置"] as const;

export default function SessionsListPage() {
  return (
    <div className="min-h-screen bg-[#E8EDF6] p-4 text-slate-700">
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-[1440px] overflow-hidden rounded-3xl border border-[#DFE6F2] bg-[#F8FAFD] shadow-[0_14px_30px_rgba(15,23,42,0.08)]">
        <aside className="flex w-[220px] shrink-0 flex-col border-r border-[#E4EAF5] bg-white px-5 py-6">
          <div className="mb-8 flex items-center gap-2 text-[30px] font-semibold text-slate-900">
            <span className="text-[26px] text-[#1778F2]">◠</span>
            <span className="text-[27px] tracking-tight">Eko</span>
          </div>
          <nav className="space-y-2">
            {navItems.map((item) => (
              <button
                key={item}
                type="button"
                className={`flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-[15px] ${
                  item === "会话"
                    ? "bg-[#E8F2FF] font-semibold text-[#1778F2]"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <span className="text-sm">{item === "会话" ? "◉" : "○"}</span>
                {item}
              </button>
            ))}
          </nav>
          <div className="mt-auto rounded-2xl border border-[#E6EDF8] bg-white p-3 shadow-sm">
            <div className="text-sm font-medium text-slate-800">Sarah Chen</div>
            <div className="text-xs text-slate-500">sarah.chen@eko.ai</div>
          </div>
        </aside>

        <main className="flex min-w-0 flex-1">
          <section className="min-w-0 flex-1 border-r border-[#E4EAF5] bg-white">
            <div className="border-b border-[#E8EDF6] px-6 py-5">
              <h1 className="text-[34px] font-semibold text-slate-900">会话</h1>
              <p className="mt-1 text-sm text-slate-500">查看和管理从即时消息启动而来的不同会话，并进入聊天、文稿或画布输出。</p>
            </div>

            <div className="space-y-4 px-6 py-4">
              <div className="flex items-center gap-3">
                <input
                  aria-label="搜索会话"
                  placeholder="搜索会话"
                  className="h-10 w-full rounded-xl border border-[#E3EAF6] bg-[#F8FAFD] px-4 text-sm outline-none ring-[#1677FF] placeholder:text-slate-400 focus:ring-2"
                />
                <button type="button" className="rounded-xl border border-[#E3EAF6] bg-white px-4 py-2 text-sm font-medium text-slate-600">
                  筛选
                </button>
                <button type="button" className="rounded-xl border border-[#E3EAF6] bg-white px-4 py-2 text-sm font-medium text-slate-600">
                  最新优先
                </button>
              </div>

              <div className="flex gap-2 text-xs">
                {["全部", "聊天", "文稿", "画布", "最近", "已加星标"].map((tag, idx) => (
                  <span
                    key={tag}
                    className={`rounded-full px-3 py-1 ${idx === 0 ? "bg-[#E8F2FF] font-semibold text-[#1778F2]" : "bg-[#F1F5FB] text-slate-500"}`}
                  >
                    {tag}
                  </span>
                ))}
              </div>

              <ul className="space-y-2">
                <li>
                  <Link
                    href="/sessions/q2-ads-review"
                    className="block rounded-2xl border border-[#9CC6FF] bg-[#F4F9FF] px-4 py-3 shadow-[0_0_0_1px_rgba(22,119,255,0.06)]"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-[16px] font-semibold text-slate-900">Q2 广告投放复盘</p>
                        <p className="truncate text-[13px] text-slate-500">我们仍需厘清渠道投放效果表现，再讨论优化方向。</p>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="rounded-full bg-[#E7F7EF] px-2 py-0.5 text-[#1C9C60]">聊天</span>
                        <span className="rounded-full bg-[#E8F2FF] px-2 py-0.5 text-[#1778F2]">进行中</span>
                        <span className="text-slate-500">上午 9:42</span>
                      </div>
                    </div>
                  </Link>
                </li>
                <li className="rounded-2xl border border-[#E6ECF6] bg-white px-4 py-3">
                  <p className="text-[15px] font-semibold text-slate-800">营销计划草稿 v3</p>
                  <p className="text-[13px] text-slate-500">已整合最新市场活动节奏与预算分配，待评审。</p>
                </li>
                <li className="rounded-2xl border border-[#E6ECF6] bg-white px-4 py-3">
                  <p className="text-[15px] font-semibold text-slate-800">研讨会话题与大纲</p>
                  <p className="text-[13px] text-slate-500">围绕行业趋势与客户痛点，梳理了 3 个备选主题。</p>
                </li>
                <li className="rounded-2xl border border-[#E6ECF6] bg-white px-4 py-3">
                  <p className="text-[15px] font-semibold text-slate-800">新品发布信息梳理</p>
                  <p className="text-[13px] text-slate-500">汇总新品卖点、定价策略与上市节奏，供发布会使用。</p>
                </li>
                <li className="rounded-2xl border border-[#E6ECF6] bg-white px-4 py-3">
                  <p className="text-[15px] font-semibold text-slate-800">内容内部 Brief</p>
                  <p className="text-[13px] text-slate-500">明确页面结构、核心信息与落地页内容方向。</p>
                </li>
              </ul>
            </div>
          </section>

          <section className="w-[360px] shrink-0 bg-[#FBFCFF] px-5 py-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-slate-900">Q2 广告投放复盘</h2>
                <p className="text-sm text-slate-500">飞书 · 今天上午 9:35</p>
              </div>
              <span className="text-slate-400">✕</span>
            </div>

            <div className="mt-4 flex gap-2">
              <button type="button" className="rounded-xl bg-[#1677FF] px-6 py-2 text-sm font-semibold text-white">
                打开
              </button>
              <button type="button" className="rounded-xl border border-[#DCE6F6] bg-white px-6 py-2 text-sm font-semibold text-slate-600">
                继续
              </button>
              <button type="button" className="rounded-xl border border-[#DCE6F6] bg-white px-4 py-2 text-sm font-semibold text-slate-600">
                导出
              </button>
            </div>

            <div className="mt-5 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">输出模式：</span><span className="text-[#1C9C60]">聊天</span></div>
              <div className="flex justify-between"><span className="text-slate-500">状态：</span><span className="text-[#1778F2]">进行中</span></div>
              <div className="flex justify-between"><span className="text-slate-500">来源：</span><span>飞书</span></div>
              <div className="flex justify-between"><span className="text-slate-500">最近同步：</span><span>今天 上午 9:42</span></div>
            </div>

            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">摘要</h3>
              <p className="rounded-xl border border-[#E4EAF5] bg-white p-3 text-sm leading-relaxed text-slate-600">
                复盘 Q2 各渠道广告投放表现，分析投放效果与转化情况，讨论人群、创意与预算分配的优化方向，并输出下一步行动计划。
              </p>
            </div>

            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">相关内容</h3>
              <ul className="space-y-2 text-sm">
                <li className="rounded-xl border border-[#E4EAF5] bg-white px-3 py-2">营销计划草稿 v3</li>
                <li className="rounded-xl border border-[#E4EAF5] bg-white px-3 py-2">付费搜索表现回顾</li>
                <li className="rounded-xl border border-[#E4EAF5] bg-white px-3 py-2">投放数据看板 Q2</li>
              </ul>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
