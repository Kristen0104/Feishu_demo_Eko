import { NextResponse } from "next/server";

import { deleteMockRagFile } from "@/lib/mock/mock-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function DELETE(_req: Request, ctx: { params: Promise<{ fileId: string }> }) {
  const { fileId } = await ctx.params;
  const ok = deleteMockRagFile(decodeURIComponent(fileId));
  return NextResponse.json({ code: 0, message: "ok", data: ok }, { status: 200 });
}

