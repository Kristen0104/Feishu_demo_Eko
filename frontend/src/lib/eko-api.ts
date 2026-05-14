import { getApiBaseUrl } from "@/config/eko-env";

import { readAccessToken } from "@/lib/auth-token";

/** Absolute or same-origin path for `/api/v1/...` — empty base uses relative URL (works with Next.js `rewrites`). */
export function apiUrl(path: string): string {
  const base = getApiBaseUrl();
  const p = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${p}` : p;
}

export type EkoApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

export async function fetchEkoJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = readAccessToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Authorization") && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(apiUrl(path), {
    ...init,
    headers,
  });

  let json: EkoApiEnvelope<T> | { message?: string } | null = null;
  try {
    json = (await res.json()) as EkoApiEnvelope<T>;
  } catch {
    /* non-json */
  }

  if (!json || typeof json !== "object" || !("code" in json)) {
    const error = new Error(res.status === 409 ? "任务已在处理中，请稍等。" : `Invalid response (${res.status})`) as Error & { status?: number };
    error.status = res.status;
    throw error;
  }

  if (!res.ok || json.code !== 0) {
    const msg = "message" in json && typeof json.message === "string" ? json.message : `HTTP ${res.status}`;
    const error = new Error(msg) as Error & { status?: number };
    error.status = res.status;
    throw error;
  }

  return json.data;
}
