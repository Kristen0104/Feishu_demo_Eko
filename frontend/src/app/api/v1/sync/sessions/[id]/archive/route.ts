import { NextResponse } from "next/server";

import { archiveMockSession } from "@/lib/mock/mock-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const sessionId = decodeURIComponent(id);
  const result = archiveMockSession(sessionId);
  if (!result.session) {
    return NextResponse.json({ code: 404, message: "session not found", data: null }, { status: 404 });
  }

  return NextResponse.json(
    {
      code: 0,
      message: "ok",
      data: {
        session: result.session,
        rag_file: result.createdRagFile ?? null,
      },
    },
    { status: 200 },
  );
}

