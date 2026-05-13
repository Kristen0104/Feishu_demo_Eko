"use client";

import { useEffect, useState } from "react";

import { fetchSyncSessionResult } from "@/lib/sync/fetch-session";
import type { SyncSession } from "@/lib/sync/fetch-session";
import { buildSessionDetailData } from "@/lib/sync/session-detail-from-sync";
import type { SessionDetailData } from "@/types/session-detail";
import { DocSessionWorkspace } from "./DocSessionWorkspace";

function getLoadErrorMessage(reason: string): string {
  if (reason === "unauthorized") return "当前登录状态暂不可用，请稍后重试或重新登录。";
  if (reason === "forbidden") return "当前账号暂无权限查看这个会话。";
  if (reason === "server") return "会话服务暂时不可用，正在保留上一次内容。";
  if (reason === "network") return "会话数据暂时无法刷新，正在保留上一次内容。";
  return "会话数据暂时无法刷新，正在保留上一次内容。";
}

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
  const [notFound, setNotFound] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const result = await fetchSyncSessionResult(sessionId);
      if (cancelled) return;
      setLoaded(true);

      if (result.ok) {
        setData(buildSessionDetailData(result.session));
        setNotFound(false);
        setLastError(null);
        return;
      }

      if (result.reason === "not_found") {
        setData(null);
        setNotFound(true);
        setLastError(null);
        return;
      }

      setNotFound(false);
      setLastError(getLoadErrorMessage(result.reason));
    };
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sessionId]);

  if (loaded && notFound && !data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-slate-500">
        没有找到这个真实会话。
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-2 text-center text-sm text-slate-500">
        <p>{loaded && lastError ? lastError : "正在加载真实会话数据..."}</p>
      </div>
    );
  }

  return (
    <div className="relative flex h-full min-h-0 min-w-0 flex-1 overflow-hidden">
      {lastError ? (
        <div className="absolute left-1/2 top-4 z-20 -translate-x-1/2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 shadow-sm">
          会话数据暂时无法刷新，正在保留上一次内容。
        </div>
      ) : null}
      <DocSessionWorkspace key={data.id} data={data} />
    </div>
  );
}
