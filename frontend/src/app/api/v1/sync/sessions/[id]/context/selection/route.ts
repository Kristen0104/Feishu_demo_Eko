import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  let start = 0;
  let end = 0;
  try {
    const body = (await req.json()) as { start_index?: number; end_index?: number };
    start = typeof body.start_index === "number" ? body.start_index : 0;
    end = typeof body.end_index === "number" ? body.end_index : 0;
  } catch {
    /* ignore */
  }

  return NextResponse.json({
    code: 0,
    message: "ok",
    data: {
      session_id: decodeURIComponent(id),
      message: `已基于上下文片段（${start + 1}-${end + 1}）生成演示回复（mock）。`,
    },
  });
}
