import { cookies } from "next/headers";

import { ACCESS_PERSIST_KEY, ACCESS_SESSION_KEY } from "@/lib/auth-token";

export function getServerBackendOrigin(): string {
  const raw =
    process.env.BACKEND_PROXY?.trim() ||
    process.env.NEXT_PUBLIC_EKO_API_BASE?.trim() ||
    "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
}

export async function getServerAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(ACCESS_PERSIST_KEY)?.value || cookieStore.get(ACCESS_SESSION_KEY)?.value || null;
}

export async function getServerAuthHeaders(): Promise<Record<string, string>> {
  const token = await getServerAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
