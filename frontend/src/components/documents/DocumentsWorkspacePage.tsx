"use client";

import { WorkspacePageHeader } from "@/components/workspace/workspace-page-framing";
import { cn } from "@/components/UiPrimitives";
import type { SessionListPageData } from "@/types/session";

const mockDocs = [
  { id: "1", name: "Q2 营销复盘 · Markdown", owner: "Sarah Chen", updated: "今天 14:20", source: "飞书文档", status: "已同步" },
  { id: "2", name: "客户提案 · 结构化文稿", owner: "Leo", updated: "昨天 18:06", source: "会话生成", status: "草稿" },
  { id: "3", name: "周报模板", owner: "Mia", updated: "周一", source: "本地上传", status: "已同步" },
];

export function DocumentsWorkspacePage({ data }: { data: SessionListPageData }) {
  return (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <WorkspacePageHeader
          title="文档"
          description="集中查看与管理由会话、飞书或本地上传的文稿；打开会话后可继续让 Eko 协作编辑。"
          actions={
            <button
              type="button"
              className="rounded-[12px] border border-slate-200 bg-white px-4 py-2 text-[13px] font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              新建空白文稿
            </button>
          }
        />
        <div className="min-h-0 flex-1 overflow-auto px-7 py-5">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[12px] font-medium text-slate-600">全部</span>
            <span className="rounded-full px-3 py-1 text-[12px] font-medium text-slate-500 hover:bg-slate-50">我创建的</span>
            <span className="rounded-full px-3 py-1 text-[12px] font-medium text-slate-500 hover:bg-slate-50">共享给我的</span>
          </div>

          <div className="overflow-hidden rounded-[18px] border border-slate-200/90 shadow-[0_4px_24px_rgba(15,23,42,0.04)]">
            <table className="w-full border-collapse text-left text-[13px]">
              <thead className="border-b border-slate-100 bg-slate-50/90 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-semibold">名称</th>
                  <th className="hidden px-4 py-3 font-semibold sm:table-cell">所有者</th>
                  <th className="px-4 py-3 font-semibold">更新时间</th>
                  <th className="hidden px-4 py-3 font-semibold md:table-cell">来源</th>
                  <th className="px-5 py-3 font-semibold">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white text-slate-800">
                {mockDocs.map((row) => (
                  <tr key={row.id} className="transition hover:bg-slate-50/80">
                    <td className="px-5 py-3.5">
                      <button type="button" className="font-semibold text-blue-600 hover:underline">
                        {row.name}
                      </button>
                    </td>
                    <td className="hidden px-4 py-3.5 text-slate-600 sm:table-cell">{row.owner}</td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-slate-500">{row.updated}</td>
                    <td className="hidden px-4 py-3.5 text-slate-500 md:table-cell">{row.source}</td>
                    <td className="px-5 py-3.5">
                      <span
                        className={cn(
                          "inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
                          row.status === "已同步" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800",
                        )}
                      >
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-6 text-center text-[12px] text-slate-400">以上为演示数据；接入后端文档列表后将替换为实时内容。</p>
        </div>
      </div>
  );
}
