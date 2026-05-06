import { SessionDetailShell } from "@/components/session-detail/SessionDetailShell";
import type { SyncSession } from "@/lib/sync/fetch-session";

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_PROXY?.trim() ||
    process.env.NEXT_PUBLIC_EKO_API_BASE?.trim() ||
    "http://39.104.87.235:8000";
  return raw.replace(/\/$/, "");
}

async function fetchInitialSession(sessionId: string): Promise<SyncSession | null> {
  try {
    const response = await fetch(`${getBackendOrigin()}/api/v1/sync/sessions/${encodeURIComponent(sessionId)}`, {
      cache: "no-store",
    });
    const body = (await response.json().catch(() => null)) as { code?: number; data?: SyncSession | null } | null;
    if (!response.ok || !body || body.code !== 0 || !body.data) return null;
    return body.data;
  } catch {
    return null;
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
