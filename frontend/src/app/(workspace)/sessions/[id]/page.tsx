import { SessionDetailShell } from "@/components/session-detail/SessionDetailShell";
import type { SyncSession } from "@/lib/sync/fetch-session";

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_PROXY?.trim() ||
    process.env.NEXT_PUBLIC_EKO_API_BASE?.trim() ||
    "";
  return raw.replace(/\/$/, "");
}

async function fetchInitialSession(sessionId: string): Promise<SyncSession | null> {
  const origin = getBackendOrigin();
  if (!origin) return null;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1500);
  try {
    const response = await fetch(`${origin}/api/v1/sync/sessions/${encodeURIComponent(sessionId)}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    const body = (await response.json().catch(() => null)) as { code?: number; data?: SyncSession | null } | null;
    if (!response.ok || !body || body.code !== 0 || !body.data) return null;
    return body.data;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sessionId = decodeURIComponent(id);
  const initialSession = await fetchInitialSession(sessionId);
  return <SessionDetailShell sessionId={sessionId} initialSession={initialSession} />;
}
