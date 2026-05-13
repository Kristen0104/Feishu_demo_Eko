import { EkoSquircleMark } from "@/components/login/brand-icons";
import { DetailTabKey, SessionDetailData } from "@/types/session-detail";

function ToolIcon({ type }: { type: "like" | "dislike" | "copy" }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 18 18",
    fill: "none",
    "aria-hidden": true,
  };
  switch (type) {
    case "like":
      return (
        <svg {...common}>
          <path d="M6.6 8V15H4.2C3.54 15 3 14.46 3 13.8V9.2C3 8.54 3.54 8 4.2 8H6.6ZM8 15L12.2 15C12.86 15 13.43 14.54 13.57 13.9L14.36 10.3C14.57 9.34 13.84 8.43 12.86 8.43H10.7L11.08 6.07C11.19 5.36 10.96 4.64 10.45 4.13L9.8 3.48L8 8.01V15Z" stroke="#64748B" strokeWidth="1.4" strokeLinejoin="round" />
        </svg>
      );
    case "dislike":
      return (
        <svg {...common}>
          <path d="M11.4 10V3H13.8C14.46 3 15 3.54 15 4.2V8.8C15 9.46 14.46 10 13.8 10H11.4ZM10 3L5.8 3C5.14 3 4.57 3.46 4.43 4.1L3.64 7.7C3.43 8.66 4.16 9.57 5.14 9.57H7.3L6.92 11.93C6.81 12.64 7.04 13.36 7.55 13.87L8.2 14.52L10 9.99V3Z" stroke="#64748B" strokeWidth="1.4" strokeLinejoin="round" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <rect x="4.2" y="4.2" width="8.2" height="8.2" rx="1.8" stroke="#64748B" strokeWidth="1.4" />
          <path d="M7 7H13.4V13.4" stroke="#64748B" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
      );
  }
}

function CanvasMiniIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="6" height="6" rx="1.6" stroke="#8B5CF6" strokeWidth="1.6" />
      <rect x="13" y="3" width="6" height="6" rx="1.6" stroke="#8B5CF6" strokeWidth="1.6" />
      <rect x="3" y="13" width="6" height="6" rx="1.6" stroke="#8B5CF6" strokeWidth="1.6" />
      <rect x="13" y="13" width="6" height="6" rx="1.6" stroke="#8B5CF6" strokeWidth="1.6" />
    </svg>
  );
}

function DocMiniIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <path d="M6 3.5H13.8L17 6.7V18.5H6V3.5Z" stroke="#2563EB" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M13.6 3.5V6.9H17" stroke="#2563EB" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export function DetailOutputSurface({
  data,
  activeTab,
}: {
  data: SessionDetailData;
  activeTab: DetailTabKey;
}) {
  if (activeTab === "chat") {
    return (
      <div className="space-y-5">
        <div>
          <h3 className="text-[18px] font-semibold text-slate-950">{data.chatReply.title}</h3>
        </div>

        <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_8px_24px_rgba(15,23,42,0.03)]">
          <div className="flex items-start gap-4">
            <EkoSquircleMark className="h-16 w-16 rounded-2xl shadow-[0_10px_28px_rgba(37,99,235,0.14)]" />
            <div className="min-w-0 flex-1">
              <p className="text-[18px] font-semibold leading-9 text-slate-900">{data.chatReply.body}</p>
              <div className="mt-5 flex items-center justify-between gap-4">
                <p className="text-[13px] text-slate-400">{data.chatReply.source}</p>
                <div className="flex items-center gap-2">
                  <button className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-slate-200 bg-white hover:bg-slate-50">
                    <ToolIcon type="like" />
                  </button>
                  <button className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-slate-200 bg-white hover:bg-slate-50">
                    <ToolIcon type="dislike" />
                  </button>
                  <button className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-slate-200 bg-white hover:bg-slate-50">
                    <ToolIcon type="copy" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-[22px] border border-slate-200 bg-slate-50/80 px-6 py-5 shadow-[0_6px_18px_rgba(15,23,42,0.02)]">
            <div className="flex items-start gap-4">
              <DocMiniIcon />
              <div>
                <p className="text-[17px] font-semibold text-slate-700">文档区域</p>
                <p className="mt-2 text-[14px] text-slate-400">当前聊天模式未刷新</p>
              </div>
            </div>
          </div>

          <div className="rounded-[22px] border border-slate-200 bg-slate-50/80 px-6 py-5 shadow-[0_6px_18px_rgba(15,23,42,0.02)]">
            <div className="flex items-start gap-4">
              <CanvasMiniIcon />
              <div>
                <p className="text-[17px] font-semibold text-slate-700">画布区域</p>
                <p className="mt-2 text-[14px] text-slate-400">当前聊天模式未刷新</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === "doc") {
    return (
      <div className="space-y-5">
        <div>
          <h3 className="text-[18px] font-semibold text-slate-950">文稿预览</h3>
        </div>
        <div className="rounded-[24px] border border-slate-200 bg-white px-8 py-8 shadow-[0_8px_24px_rgba(15,23,42,0.03)]">
          <h4 className="text-[26px] font-semibold tracking-[-0.04em] text-slate-950">{data.document.title}</h4>
          <div className="mt-7 space-y-7">
            {data.document.sections.map((section, secIdx) => (
              <section key={`doc-sec-${secIdx}-${section.title}`}>
                <h5 className="text-[18px] font-semibold text-slate-950">{section.title}</h5>
                {section.body && <p className="mt-3 text-[15px] leading-8 text-slate-600">{section.body}</p>}
                {section.bullets && (
                  <ul className="mt-4 space-y-3 pl-5 text-[14px] leading-7 text-slate-600">
                    {section.bullets.map((item, bi) => (
                      <li key={`doc-sec-${secIdx}-b-${bi}`} className="list-disc">
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-[18px] font-semibold text-slate-950">{data.canvas.title}</h3>
        <button className="rounded-full border border-violet-200 bg-violet-50 px-4 py-2 text-[13px] font-semibold text-violet-600">
          在画布中打开
        </button>
      </div>

      <div className="rounded-[24px] border border-dashed border-slate-200 bg-[radial-gradient(circle_at_top,#F8FAFF_0%,#F7FAFF_42%,#F4F7FC_100%)] p-5 shadow-[0_8px_24px_rgba(15,23,42,0.03)]">
        <div className="grid gap-4 md:grid-cols-3">
          {data.canvas.nodes.map((node, index) => (
            <div key={node.id} className="relative">
              {index % 3 !== 2 && (
                <div className="absolute right-[-20px] top-1/2 hidden h-[2px] w-8 -translate-y-1/2 bg-slate-300 md:block" />
              )}
              {index < 3 && (
                <div className="absolute bottom-[-10px] left-1/2 hidden h-5 w-[2px] -translate-x-1/2 border-l border-dashed border-slate-300 md:block" />
              )}
              <div className="rounded-[22px] border border-slate-200 bg-white px-5 py-5 shadow-[0_8px_20px_rgba(15,23,42,0.04)]">
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-[14px] font-semibold text-slate-700">
                    {node.index}
                  </span>
                  <span className="text-[18px] font-semibold text-violet-500">{node.icon === "alert" ? "!" : node.icon === "check" ? "◌" : node.icon === "calendar" ? "✓" : node.icon === "rocket" ? "✦" : node.icon === "spark" ? "✷" : "↗"}</span>
                </div>
                <h4 className="mt-4 text-[17px] font-semibold text-slate-950">{node.title}</h4>
                <ul className="mt-4 space-y-2 text-[13px] leading-6 text-slate-600">
                  {node.bullets.map((bullet, bi) => (
                    <li key={`${node.id}-b-${bi}`}>• {bullet}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 text-left shadow-[0_6px_16px_rgba(15,23,42,0.03)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">输入</p>
            <p className="mt-2 text-[13px] text-slate-600">飞书群讨论</p>
          </div>
          <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 text-left shadow-[0_6px_16px_rgba(15,23,42,0.03)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Eko</p>
            <p className="mt-2 text-[13px] text-slate-600">意图路由 + 知识补齐 + 内容生成</p>
          </div>
          <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 text-left shadow-[0_6px_16px_rgba(15,23,42,0.03)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">输出</p>
            <p className="mt-2 text-[13px] text-slate-600">画布预览 + 项目记录同步</p>
          </div>
        </div>
      </div>
    </div>
  );
}
