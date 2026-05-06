import { NextResponse } from "next/server";

import { encodeAgentChatDemoStream } from "@/lib/mock/demo-stream";
import type { AgentChatStreamEvent } from "@/lib/agent/sse-stream";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type ChatBody = {
  session_id?: string;
  message?: string;
};

function chooseArtifact(message: string): {
  kind: "ppt" | "board" | "docx";
  intent: string;
  title: string;
  artifact: Record<string, unknown>;
  assistantHint: string;
} {
  const text = message.toLowerCase();
  if (text.includes("ppt") || text.includes("幻灯片") || text.includes("演示文稿")) {
    return {
      kind: "ppt",
      intent: "ppt",
      title: "AI PPT（演示）",
      artifact: {
        kind: "ppt",
        status: "completed",
        progress: 1,
        job_id: "demo-ppt-job",
        download_url: null,
        current_step: "已完成导出预览（演示模式）",
      },
      assistantHint: "我已经生成一页可用的预览样式（演示），你可以在右侧查看幻灯片缩略图与主预览图。",
    };
  }
  if (
    text.includes("画板") ||
    text.includes("画布") ||
    text.includes("白板") ||
    text.includes("流程图") ||
    text.includes("board") ||
    text.includes("canvas")
  ) {
    return {
      kind: "board",
      intent: "board",
      title: "飞书画板（演示）",
      artifact: {
        kind: "board",
        status: "completed",
        progress: 1,
        whiteboard_id: "demo-wb-1",
        preview_url: "/api/v1/mock/board/preview",
        sharing_url: "/canvas?session=demo-session&user=demo@eko.local&owner=demo@eko.local",
        current_step: "画板预览已就绪（演示模式）",
      },
      assistantHint: "我已经准备好画板预览资源（演示）。你可以在中间预览区域查看图片，并点击「打开画布」进入协同画布页。",
    };
  }

  return {
    kind: "docx",
    intent: "doc",
    title: "文稿草稿（演示）",
    artifact: {
      kind: "docx",
      status: "completed",
      progress: 1,
      content:
        "## 演示输出\n\n- 目标：把对话转化为可交付的结构化结果。\n- 关键假设：演示模式不接后端。\n- 下一步：接入真实 Agent / 飞书 API。\n",
      download_url: null,
      current_step: "文稿已生成（演示模式）",
    },
    assistantHint: "下面是演示文稿产物（Markdown）。你可以在右侧切换到文档视图查看排版效果。",
  };
}

export async function POST(req: Request) {
  let body: ChatBody = {};
  try {
    body = (await req.json()) as ChatBody;
  } catch {
    body = {};
  }

  const sessionId = typeof body.session_id === "string" ? body.session_id : "demo-session";
  const message = typeof body.message === "string" ? body.message : "";

  const picked = chooseArtifact(message);

  const responseArtifact = {
    ...picked.artifact,
    title: picked.title,
    intent: picked.intent,
    result_summary: picked.assistantHint,
  };

  const events: AgentChatStreamEvent[] = [
    {
      event: "turn.started",
      status: "running",
      message: "收到，我将按演示流程推进（mock）。",
      payload: { planning_enabled: true },
    },
    {
      event: "intent.recognized",
      status: "running",
      message: `识别意图：${picked.intent}`,
      payload: { intent: picked.intent },
    },
    {
      event: "retrieval.started",
      status: "running",
      message: "正在检索演示知识库（mock）。",
      payload: {},
    },
    {
      event: "retrieval.completed",
      status: "running",
      message: "检索完成（演示数据）。",
      payload: { sources: [{ title: "内部策略备忘录（mock）", score: 0.82 }] },
    },
    {
      event: "plan.created",
      status: "running",
      message: "已生成执行计划（演示）。",
      payload: {
        plan: {
          steps: [
            { id: "1", title: "理解输入与约束", description: "抽取目标与输出形态", status: "completed" },
            { id: "2", title: "生成结构化产物", description: "输出可展示的演示结果", status: "running" },
            { id: "3", title: "给出下一步建议", description: "提示如何接入真实后端", status: "pending" },
          ],
        },
      },
    },
    {
      event: "tool.started",
      status: "running",
      message: `正在调用能力：${picked.kind}`,
      payload: { tool: picked.kind },
    },
    {
      event: "result.created",
      status: "running",
      payload: {
        response: {
          session_id: sessionId,
          status: "completed",
          message: picked.assistantHint,
          artifact: responseArtifact,
        },
      },
    },
  ];

  return new NextResponse(encodeAgentChatDemoStream(events), {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-store, no-transform",
      Connection: "keep-alive",
    },
  });
}
