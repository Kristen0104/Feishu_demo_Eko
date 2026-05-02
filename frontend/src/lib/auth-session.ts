/**
 * 登录态在浏览器中的两种保存方式（与 Zustand auth 字段解耦，避免误把「不保持登录」写进 localStorage）：
 * - 勾选保持登录：localStorage，15 天有效
 * - 不勾选：仅 sessionStorage，关闭该浏览上下文后需重新输入密码
 */

const PERSIST_KEY = "eko-auth-persist-v1";
const SESSION_KEY = "eko-auth-session-v1";

const FIFTEEN_DAYS_MS = 15 * 24 * 60 * 60 * 1000;

export function saveAuthAfterLogin(email: string, remember: boolean): void {
  if (typeof window === "undefined") return;
  const normalized = email.toLowerCase();
  if (remember) {
    const expiresAt = Date.now() + FIFTEEN_DAYS_MS;
    localStorage.setItem(PERSIST_KEY, JSON.stringify({ email: normalized, expiresAt }));
    sessionStorage.removeItem(SESSION_KEY);
  } else {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ email: normalized, at: Date.now() }));
    localStorage.removeItem(PERSIST_KEY);
  }
}

export function readAuth(): { email: string } | null {
  if (typeof window === "undefined") return null;

  const sessionRaw = sessionStorage.getItem(SESSION_KEY);
  if (sessionRaw) {
    try {
      const { email } = JSON.parse(sessionRaw) as { email?: string };
      if (email && typeof email === "string") {
        return { email: email.toLowerCase() };
      }
    } catch {
      sessionStorage.removeItem(SESSION_KEY);
    }
  }

  const persistRaw = localStorage.getItem(PERSIST_KEY);
  if (persistRaw) {
    try {
      const parsed = JSON.parse(persistRaw) as { email?: string; expiresAt?: number };
      if (parsed.email && typeof parsed.expiresAt === "number") {
        if (Date.now() < parsed.expiresAt) {
          return { email: parsed.email.toLowerCase() };
        }
      }
      localStorage.removeItem(PERSIST_KEY);
    } catch {
      localStorage.removeItem(PERSIST_KEY);
    }
  }

  return null;
}

export function clearAuthStorage(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(PERSIST_KEY);
  sessionStorage.removeItem(SESSION_KEY);
}
