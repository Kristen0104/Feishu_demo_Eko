import { NextRequest, NextResponse } from "next/server";

import { ACCESS_PERSIST_KEY, ACCESS_SESSION_KEY } from "@/lib/auth-token";
import { AUTH_PERSIST_KEY, AUTH_SESSION_KEY } from "@/lib/auth-session";
import { getServerBackendOrigin } from "@/lib/server/backend";

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

function readAccessToken(request: NextRequest): string | null {
  return request.cookies.get(ACCESS_PERSIST_KEY)?.value || request.cookies.get(ACCESS_SESSION_KEY)?.value || null;
}

function buildErrorRedirect(request: NextRequest, mode: "login" | "bind" = "login"): NextResponse {
  const target = mode === "bind" ? "/profile/security?feishu_bind=error" : "/login?feishu_error=1";
  return NextResponse.redirect(new URL(target, getPublicOrigin(request)), { status: 302 });
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
  const mode = getParam(searchParams, "mode") === "bind" ? "bind" : "login";

  if (error || !code || !state) {
    return buildErrorRedirect(request, mode);
  }

  try {
    const backendOrigin = getServerBackendOrigin();
    const endpoint = mode === "bind" ? "/api/v1/auth/feishu/bind" : "/api/v1/auth/feishu/login";
    const token = mode === "bind" ? readAccessToken(request) : null;
    if (mode === "bind" && !token) {
      return buildErrorRedirect(request, mode);
    }

    const response = await fetch(`${backendOrigin}${endpoint}`, {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ code, state }),
    });

    const body = (await response.json().catch(() => null)) as FeishuAuthTokenResponse | null;
    if (!response.ok || !body || body.code !== 0 || !body.data?.access_token) {
      if (mode === "bind" && body?.code === 0) {
        return NextResponse.redirect(new URL("/profile/security?feishu_bind=success", getPublicOrigin(request)), { status: 302 });
      }
      throw new Error(body?.message || `HTTP ${response.status}`);
    }

    if (mode === "bind") {
      return NextResponse.redirect(new URL("/profile/security?feishu_bind=success", getPublicOrigin(request)), { status: 302 });
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
    return buildErrorRedirect(request, mode);
  }
}
