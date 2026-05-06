import { NextResponse } from "next/server";

import { getMockSession } from "@/lib/mock/mock-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const sessionId = decodeURIComponent(id);
  const item = getMockSession(sessionId);
  return NextResponse.json(
    {
      code: 0,
      data: item,
      message: "ok",
    },
    { status: 200 },
  );
}

