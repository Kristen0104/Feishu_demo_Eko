import { encodeSseJsonLines } from "@/lib/mock/demo-stream";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type GenBody = {
  session_id?: string;
};

export async function POST(req: Request) {
  let sessionId = "demo-session";
  try {
    const body = (await req.json()) as GenBody;
    if (typeof body.session_id === "string") sessionId = body.session_id;
  } catch {
    /* ignore */
  }

  const markdown =
    "# 演示文稿（mock）\n\n## 要点\n- 这是前端静态 SSE 输出。\n- 不接后端也能展示「生成中文稿」体验。\n\n## 下一步\n把该路由替换为真实 FastAPI SSE。\n";

  const lines = [
    { session_id: sessionId, status: "generating" },
    { content: markdown.slice(0, 40) },
    { content: markdown.slice(40, 90) },
    { content: markdown.slice(90) },
    { status: "completed" as const },
  ];

  return new Response(encodeSseJsonLines(lines), {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-store, no-transform",
      Connection: "keep-alive",
    },
  });
}
