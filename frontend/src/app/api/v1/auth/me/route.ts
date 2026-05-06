import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    code: 0,
    message: "ok",
    data: {
      email: "demo@eko.local",
      name: "Eko Demo User",
      avatar_url: null,
      tenant: "eko-demo",
    },
  });
}
