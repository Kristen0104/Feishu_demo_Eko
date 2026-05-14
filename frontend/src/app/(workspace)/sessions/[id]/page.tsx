import { SessionDetailShell } from "@/components/session-detail/SessionDetailShell";
import { getServerAuthHeaders, getServerBackendOrigin } from "@/lib/server/backend";
import type { SyncSession } from "@/lib/sync/fetch-session";

async function fetchInitialSession(sessionId: string): Promise<SyncSession | null> {
  try {
    const headers = await getServerAuthHeaders();
    const response = await fetch(`${getServerBackendOrigin()}/api/v1/sync/sessions/${encodeURIComponent(sessionId)}`, {
      cache: "no-store",
      headers,
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
