import { NextResponse } from "next/server";

import { listMockSessions } from "@/lib/mock/mock-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json(
    {
      code: 0,
      data: listMockSessions(),
      message: "ok",
    },
    { status: 200 },
  );
}

