import { deleteCookie, readCookie, setCookie } from "@/lib/browser-cookies";

export const ACCESS_PERSIST_KEY = "eko-access-token";
export const ACCESS_SESSION_KEY = "eko-access-token-session";
const ACCESS_COOKIE_MAX_AGE_SECONDS = 15 * 24 * 60 * 60;

export function readAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return (
      readCookie(ACCESS_PERSIST_KEY) ??
      readCookie(ACCESS_SESSION_KEY) ??
      sessionStorage.getItem(ACCESS_SESSION_KEY) ??
      localStorage.getItem(ACCESS_PERSIST_KEY)
    );
  } catch {
    return null;
  }
}

export function saveAccessToken(token: string, remember: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (remember) {
      localStorage.setItem(ACCESS_PERSIST_KEY, token);
      sessionStorage.removeItem(ACCESS_SESSION_KEY);
      deleteCookie(ACCESS_SESSION_KEY);
      setCookie(ACCESS_PERSIST_KEY, token, { maxAgeSeconds: ACCESS_COOKIE_MAX_AGE_SECONDS });
    } else {
      sessionStorage.setItem(ACCESS_SESSION_KEY, token);
      localStorage.removeItem(ACCESS_PERSIST_KEY);
      deleteCookie(ACCESS_PERSIST_KEY);
      setCookie(ACCESS_SESSION_KEY, token);
    }
  } catch {
    /* ignore */
  }
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(ACCESS_PERSIST_KEY);
    sessionStorage.removeItem(ACCESS_SESSION_KEY);
    deleteCookie(ACCESS_PERSIST_KEY);
    deleteCookie(ACCESS_SESSION_KEY);
  } catch {
    /* ignore */
  }
}
