import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    ok: true,
    app: "Eko Workspace",
    timestamp: new Date().toISOString(),
  });
}
