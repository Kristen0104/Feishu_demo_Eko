import { NextRequest, NextResponse } from "next/server";

import { ACCESS_PERSIST_KEY, ACCESS_SESSION_KEY } from "@/lib/auth-token";
import { AUTH_PERSIST_KEY, AUTH_SESSION_KEY } from "@/lib/auth-session";

const REMEMBER_SECONDS = 15 * 24 * 60 * 60;

type FeishuAuthTokenResponse = {
  code: number;
  message: string;
  data?: {
    access_token?: string;
    user?: {
      user_id?: string;
      display_name?: string;
      feishu_user_id?: string;
      email?: string | null;
    };
  };
};

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_PROXY?.trim() ||
    process.env.NEXT_PUBLIC_EKO_API_BASE?.trim() ||
    "http://39.104.87.235:8000";
  return raw.replace(/\/$/, "");
}

function getPublicOrigin(request: NextRequest): string {
  const forwardedHost = request.headers.get("x-forwarded-host")?.trim();
  const forwardedProto = request.headers.get("x-forwarded-proto")?.trim();
  const host = forwardedHost || request.headers.get("host") || new URL(request.url).host;
  const protocol = forwardedProto || new URL(request.url).protocol.replace(":", "");
  return `${protocol}://${host}`;
}

function getParam(searchParams: URLSearchParams, key: string): string | null {
  const value = searchParams.get(key);
  return value && value.trim() ? value.trim() : null;
}

function buildErrorRedirect(request: NextRequest): NextResponse {
  return NextResponse.redirect(new URL("/login?feishu_error=1", getPublicOrigin(request)), { status: 302 });
}

function setAuthCookies(
  response: NextResponse,
  request: NextRequest,
  accessToken: string,
  loginLabel: string,
): void {
  const secure = request.nextUrl.protocol === "https:";
  const authPayload = JSON.stringify({
    email: loginLabel.toLowerCase(),
    expiresAt: Date.now() + REMEMBER_SECONDS * 1000,
  });

  response.cookies.set(ACCESS_PERSIST_KEY, accessToken, {
    path: "/",
    sameSite: "lax",
    secure,
    maxAge: REMEMBER_SECONDS,
  });
  response.cookies.set(AUTH_PERSIST_KEY, authPayload, {
    path: "/",
    sameSite: "lax",
    secure,
    maxAge: REMEMBER_SECONDS,
  });
  response.cookies.set(ACCESS_SESSION_KEY, "", {
    path: "/",
    sameSite: "lax",
    secure,
    maxAge: 0,
  });
  response.cookies.set(AUTH_SESSION_KEY, "", {
    path: "/",
    sameSite: "lax",
    secure,
    maxAge: 0,
  });
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = getParam(searchParams, "code");
  const state = getParam(searchParams, "state");
  const error = getParam(searchParams, "error");

  if (error || !code || !state) {
    return buildErrorRedirect(request);
  }

  try {
    const backendOrigin = getBackendOrigin();
    const response = await fetch(`${backendOrigin}/api/v1/auth/feishu/login`, {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ code, state }),
    });

    const body = (await response.json().catch(() => null)) as FeishuAuthTokenResponse | null;
    if (!response.ok || !body || body.code !== 0 || !body.data?.access_token) {
      throw new Error(body?.message || `HTTP ${response.status}`);
    }

    const accessToken = body.data.access_token;
    const user = body.data.user ?? {};
    const loginLabel =
      user.email?.trim() ||
      user.display_name?.trim() ||
      user.feishu_user_id?.trim() ||
      user.user_id?.trim() ||
      "feishu-user";

    const redirectResponse = NextResponse.redirect(new URL("/home", getPublicOrigin(request)), { status: 302 });
    setAuthCookies(redirectResponse, request, accessToken, loginLabel);
    return redirectResponse;
  } catch {
    return buildErrorRedirect(request);
  }
}
