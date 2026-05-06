"use client";

import { useEffect, useState } from "react";

import { getApiBaseUrl } from "@/config/eko-env";
import { fetchSyncSession } from "@/lib/sync/fetch-session";
import type { SyncSession } from "@/lib/sync/fetch-session";
import { buildSessionDetailData } from "@/lib/sync/session-detail-from-sync";
import type { SessionDetailData } from "@/types/session-detail";
import { DocSessionWorkspace } from "./DocSessionWorkspace";

export function SessionDetailShell({
  sessionId,
  initialSession,
}: {
  sessionId: string;
  initialSession?: SyncSession | null;
}) {
  const [data, setData] = useState<SessionDetailData | null>(
    initialSession ? buildSessionDetailData(initialSession) : null,
  );
  const [loaded, setLoaded] = useState(Boolean(initialSession));

  useEffect(() => {
    let cancelled = false;
    const shouldPoll = Boolean(getApiBaseUrl());
    let lastSignature = "";
    const load = async () => {
      const session = await fetchSyncSession(sessionId);
      if (cancelled) return;
      setLoaded(true);
      if (!session) {
        setData(null);
        return;
      }
      // Avoid re-render thrash in mock/offline mode by only updating when something changed.
      const signature = `${session.session_id}|${session.updated_at}|${session.artifact?.status ?? ""}|${session.artifact?.progress ?? ""}`;
      if (signature === lastSignature) return;
      lastSignature = signature;
      setData(buildSessionDetailData(session));
    };
    void load();
    if (!shouldPoll) return () => {
      cancelled = true;
    };
    const timer = window.setInterval(() => void load(), 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sessionId]);

  if (loaded && !data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-slate-500">
        没有找到这个真实会话。
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-slate-500">
        正在加载真实会话数据...
      </div>
    );
  }

  return <DocSessionWorkspace key={data.id} data={data} />;
}
