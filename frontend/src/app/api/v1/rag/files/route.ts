import { NextResponse } from "next/server";

import { listMockRagFiles } from "@/lib/mock/mock-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({ code: 0, message: "ok", data: listMockRagFiles() }, { status: 200 });
}

