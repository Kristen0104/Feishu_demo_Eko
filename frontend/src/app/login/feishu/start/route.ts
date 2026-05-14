import { NextRequest, NextResponse } from "next/server";

import { getServerBackendOrigin } from "@/lib/server/backend";

type FeishuLoginUrlResponse = {
  code: number;
  message: string;
  data?: {
    authorize_url?: string;
    state?: string;
    expires_in?: number;
  };
};

async function readFeishuLoginUrl(redirectUri: string): Promise<string> {
  const backendOrigin = getServerBackendOrigin();
  const response = await fetch(
    `${backendOrigin}/api/v1/auth/feishu/login-url?redirect_uri=${encodeURIComponent(redirectUri)}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const body = (await response.json().catch(() => null)) as FeishuLoginUrlResponse | null;
  if (!response.ok || !body || body.code !== 0 || !body.data?.authorize_url) {
    throw new Error(body?.message || `HTTP ${response.status}`);
  }

  return body.data.authorize_url;
}

export async function GET(request: NextRequest) {
  const mode = request.nextUrl.searchParams.get("mode") === "bind" ? "bind" : "login";
  const forwardedHost = request.headers.get("x-forwarded-host")?.trim();
  const forwardedProto = request.headers.get("x-forwarded-proto")?.trim();
  const host = forwardedHost || request.headers.get("host") || new URL(request.url).host;
  const protocol = forwardedProto || new URL(request.url).protocol.replace(":", "");
  const redirectUri = `${protocol}://${host}/login/feishu/callback${mode === "bind" ? "?mode=bind" : ""}`;

  try {
    const authorizeUrl = await readFeishuLoginUrl(redirectUri);
    return NextResponse.redirect(authorizeUrl, { status: 302 });
  } catch {
    return NextResponse.redirect(new URL("/login?feishu_error=1", request.url), { status: 302 });
  }
}
