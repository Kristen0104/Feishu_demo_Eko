import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  let sessionId = "demo-session";
  try {
    const body = (await req.json()) as { session_id?: string };
    if (typeof body.session_id === "string") sessionId = body.session_id;
  } catch {
    /* ignore */
  }

  return NextResponse.json({
    code: 0,
    message: "ok",
    data: {
      session_id: sessionId,
      status: "completed" as const,
      message: "文档已同步（演示模式，无真实飞书落库）",
      document_url: "https://example.com/mock-feishu-doc",
    },
  });
}
