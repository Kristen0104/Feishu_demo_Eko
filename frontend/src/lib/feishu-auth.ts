import { apiUrl } from "@/lib/eko-api";

const FEISHU_LOGIN_DRAFT_KEY = "eko-feishu-login-draft-v1";

export type FeishuLoginUrlData = {
  authorize_url: string;
  state: string;
  expires_in: number;
};

export type FeishuAuthUser = {
  user_id: string;
  display_name: string;
  feishu_user_id: string;
  email?: string | null;
  avatar_url?: string | null;
};

export type FeishuAuthTokenData = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: FeishuAuthUser;
};

export type FeishuLoginDraft = {
  authorizeUrl: string;
  redirectUri: string;
  state: string;
  savedAt: string;
};

type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

function readEnvelope<T>(body: unknown, fallbackMessage: string): T {
  if (!body || typeof body !== "object" || !("code" in body)) {
    throw new Error(fallbackMessage);
  }

  const payload = body as ApiEnvelope<T>;
  if (payload.code !== 0) {
    throw new Error(payload.message || fallbackMessage);
  }

  return payload.data;
}

function readErrorMessage(body: unknown, fallbackMessage: string): string {
  if (!body || typeof body !== "object" || !("code" in body)) {
    return fallbackMessage;
  }

  const payload = body as Partial<ApiEnvelope<unknown>>;
  return typeof payload.message === "string" && payload.message.trim() ? payload.message : fallbackMessage;
}

export function resolveFeishuRedirectUri(): string {
  if (typeof window === "undefined") {
    return "/login/feishu/callback";
  }

  return new URL("/login/feishu/callback", window.location.origin).toString();
}

export function saveFeishuLoginDraft(draft: Omit<FeishuLoginDraft, "savedAt">): void {
  if (typeof window === "undefined") return;

  try {
    const payload: FeishuLoginDraft = {
      ...draft,
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(FEISHU_LOGIN_DRAFT_KEY, JSON.stringify(payload));
  } catch {
    /* ignore */
  }
}

export function readFeishuLoginDraft(): FeishuLoginDraft | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = localStorage.getItem(FEISHU_LOGIN_DRAFT_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as Partial<FeishuLoginDraft>;
    if (!parsed.authorizeUrl || !parsed.redirectUri || !parsed.state || !parsed.savedAt) {
      return null;
    }

    return {
      authorizeUrl: parsed.authorizeUrl,
      redirectUri: parsed.redirectUri,
      state: parsed.state,
      savedAt: parsed.savedAt,
    };
  } catch {
    return null;
  }
}

export function clearFeishuLoginDraft(): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.removeItem(FEISHU_LOGIN_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

export async function requestFeishuLoginUrl(redirectUri?: string): Promise<FeishuLoginUrlData> {
  const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : "";
  const response = await fetch(apiUrl(`/api/v1/auth/feishu/login-url${query}`), {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  const body = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    throw new Error(readErrorMessage(body, `HTTP ${response.status}`));
  }

  return readEnvelope<FeishuLoginUrlData>(body, "获取飞书登录地址失败");
}

export async function exchangeFeishuLogin(code: string, state: string, redirectUri?: string): Promise<FeishuAuthTokenData> {
  const response = await fetch(apiUrl("/api/v1/auth/feishu/login"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      code,
      state,
      ...(redirectUri ? { redirect_uri: redirectUri } : {}),
    }),
  });

  const body = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    throw new Error(readErrorMessage(body, `HTTP ${response.status}`));
  }

  return readEnvelope<FeishuAuthTokenData>(body, "飞书登录失败");
}
