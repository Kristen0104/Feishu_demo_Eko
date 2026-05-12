"use client";

import Link from "next/link";

import { WorkspacePageHeader } from "@/components/workspace/workspace-page-framing";
import { cn } from "@/components/UiPrimitives";
import type { SessionItem, SessionListPageData } from "@/types/session";

function getDocumentSessions(data: SessionListPageData): SessionItem[] {
  return data.sections.flatMap((section) => section.items).filter((item) => item.kind === "doc");
}

export function DocumentsWorkspacePage({ data }: { data: SessionListPageData }) {
  const docs = getDocumentSessions(data);

  return (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <WorkspacePageHeader
          title="文档"
          description="集中查看由后端同步会话产出的文稿；打开会话后可继续让 Eko 协作编辑。"
          actions={
            <Link
              href="/sessions"
              prefetch={false}
              className="inline-flex min-h-10 w-full items-center justify-center rounded-[12px] border border-slate-200 bg-white px-4 py-2 text-[13px] font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 sm:w-auto"
            >
              从会话生成文稿
            </Link>
          }
        />
        <div className="min-h-0 flex-1 overflow-auto px-3 py-4 sm:px-5 lg:px-7 lg:py-5">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[12px] font-medium text-slate-600">全部 {docs.length}</span>
            <span className="rounded-full px-3 py-1 text-[12px] font-medium text-slate-500">已同步 {docs.filter((row) => row.status === "已同步").length}</span>
            <span className="rounded-full px-3 py-1 text-[12px] font-medium text-slate-500">生成中 {docs.filter((row) => row.status === "进行中").length}</span>
          </div>

          {docs.length === 0 ? (
            <div className="rounded-[18px] border border-slate-200/90 bg-white px-4 py-6 text-center shadow-[0_4px_24px_rgba(15,23,42,0.04)]">
              <p className="text-[14px] font-semibold text-slate-700">还没有后端同步的文稿</p>
              <p className="mx-auto mt-1 max-w-[260px] text-[12px] leading-5 text-slate-400">
                当会话产出 DOCX / PPT artifact 后，会自动出现在这里。
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-[18px] border border-slate-200/90 shadow-[0_4px_24px_rgba(15,23,42,0.04)]">
              <table className="w-full min-w-[560px] border-collapse text-left text-[13px]">
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
                  {docs.map((row) => (
                    <tr key={row.id} className="transition hover:bg-slate-50/80">
                      <td className="px-5 py-3.5">
                        <Link
                          href={row.preview.externalUrl || `/sessions/${encodeURIComponent(row.id)}`}
                          prefetch={false}
                          target={row.preview.externalUrl ? "_blank" : undefined}
                          rel={row.preview.externalUrl ? "noreferrer" : undefined}
                          className="font-semibold text-blue-600 hover:underline"
                        >
                          {row.title}
                        </Link>
                      </td>
                      <td className="hidden px-4 py-3.5 text-slate-600 sm:table-cell">{row.participants[0]?.name ?? data.user.name}</td>
                      <td className="whitespace-nowrap px-4 py-3.5 text-slate-500">{row.updatedAt}</td>
                      <td className="hidden px-4 py-3.5 text-slate-500 md:table-cell">{row.source} / {row.kindLabel}</td>
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
          )}

          <p className="mt-6 text-center text-[12px] text-slate-400">数据来自后端同步会话列表；未再使用本地 mock 文档。</p>
        </div>
      </div>
  );
}
