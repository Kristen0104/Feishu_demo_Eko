import { NextResponse } from "next/server";

import { searchMockRag } from "@/lib/mock/mock-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const query = url.searchParams.get("query") ?? "";
  const limit = Number(url.searchParams.get("limit") ?? "5");
  const response = searchMockRag(query, Number.isFinite(limit) ? Math.max(1, Math.min(20, limit)) : 5);
  return NextResponse.json({ code: 0, message: "ok", data: response }, { status: 200 });
}

