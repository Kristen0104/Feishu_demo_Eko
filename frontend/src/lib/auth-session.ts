import { deleteCookie, readCookie, setCookie } from "@/lib/browser-cookies";

/**
 * 登录态在浏览器中的两种保存方式（与 Zustand auth 字段解耦，避免误把「不保持登录」写进 localStorage）：
 * - 勾选保持登录：localStorage，15 天有效
 * - 不勾选：仅 sessionStorage，关闭该浏览上下文后需重新输入密码
 */

export const AUTH_PERSIST_KEY = "eko-auth-persist-v1";
export const AUTH_SESSION_KEY = "eko-auth-session-v1";

const FIFTEEN_DAYS_MS = 15 * 24 * 60 * 60 * 1000;
const FIFTEEN_DAYS_SECONDS = 15 * 24 * 60 * 60;

export function saveAuthAfterLogin(email: string, remember: boolean): void {
  if (typeof window === "undefined") return;
  const normalized = email.toLowerCase();
  if (remember) {
    const expiresAt = Date.now() + FIFTEEN_DAYS_MS;
    localStorage.setItem(AUTH_PERSIST_KEY, JSON.stringify({ email: normalized, expiresAt }));
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    deleteCookie(AUTH_SESSION_KEY);
    setCookie(AUTH_PERSIST_KEY, JSON.stringify({ email: normalized, expiresAt }), {
      maxAgeSeconds: FIFTEEN_DAYS_SECONDS,
    });
  } else {
    const payload = JSON.stringify({ email: normalized, at: Date.now() });
    sessionStorage.setItem(AUTH_SESSION_KEY, payload);
    localStorage.removeItem(AUTH_PERSIST_KEY);
    deleteCookie(AUTH_PERSIST_KEY);
    setCookie(AUTH_SESSION_KEY, payload);
  }
}

export function readAuth(): { email: string } | null {
  if (typeof window === "undefined") return null;

  const cookieSessionRaw = readCookie(AUTH_SESSION_KEY);
  if (cookieSessionRaw) {
    try {
      const { email } = JSON.parse(cookieSessionRaw) as { email?: string };
      if (email && typeof email === "string") {
        return { email: email.toLowerCase() };
      }
    } catch {
      deleteCookie(AUTH_SESSION_KEY);
    }
  }

  const cookiePersistRaw = readCookie(AUTH_PERSIST_KEY);
  if (cookiePersistRaw) {
    try {
      const parsed = JSON.parse(cookiePersistRaw) as { email?: string; expiresAt?: number };
      if (parsed.email && typeof parsed.expiresAt === "number") {
        if (Date.now() < parsed.expiresAt) {
          return { email: parsed.email.toLowerCase() };
        }
      }
      deleteCookie(AUTH_PERSIST_KEY);
    } catch {
      deleteCookie(AUTH_PERSIST_KEY);
    }
  }

  const sessionRaw = sessionStorage.getItem(AUTH_SESSION_KEY);
  if (sessionRaw) {
    try {
      const { email } = JSON.parse(sessionRaw) as { email?: string };
      if (email && typeof email === "string") {
        return { email: email.toLowerCase() };
      }
    } catch {
      sessionStorage.removeItem(AUTH_SESSION_KEY);
    }
  }

  const persistRaw = localStorage.getItem(AUTH_PERSIST_KEY);
  if (persistRaw) {
    try {
      const parsed = JSON.parse(persistRaw) as { email?: string; expiresAt?: number };
      if (parsed.email && typeof parsed.expiresAt === "number") {
        if (Date.now() < parsed.expiresAt) {
          return { email: parsed.email.toLowerCase() };
        }
      }
      localStorage.removeItem(AUTH_PERSIST_KEY);
    } catch {
      localStorage.removeItem(AUTH_PERSIST_KEY);
    }
  }

  return null;
}

export function clearAuthStorage(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_PERSIST_KEY);
  sessionStorage.removeItem(AUTH_SESSION_KEY);
  deleteCookie(AUTH_PERSIST_KEY);
  deleteCookie(AUTH_SESSION_KEY);
}
