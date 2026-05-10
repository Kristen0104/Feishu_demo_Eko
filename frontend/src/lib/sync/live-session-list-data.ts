import type { SessionItem, SessionListPageData, SessionParticipant, SessionSection, SessionStatus } from "@/types/session";

export type SyncSession = {
  session_id: string;
  source: string;
  title: string;
  summary: string;
  status: string;
  opened_at: string;
  updated_at: string;
  chat_id?: string | null;
  message_id?: string | null;
  context_size?: number;
  instruction?: string | null;
  intent?: string | null;
  artifact?: {
    kind?: string | null;
    intent?: string | null;
    job_id?: string | null;
    status?: string | null;
    progress?: number | null;
    current_step?: string | null;
    download_url?: string | null;
    error_message?: string | null;
    [key: string]: unknown;
  } | null;
  messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
  }>;
  context_messages?: Array<{
    role: string;
    content: string;
    timestamp?: number | null;
  }>;
};

function getBackendOrigin(): string {
  const raw =
    process.env.BACKEND_PROXY?.trim() ||
    process.env.NEXT_PUBLIC_EKO_API_BASE?.trim() ||
    "http://39.104.87.235:8000";
  return raw.replace(/\/$/, "");
}

function mapStatus(status: string): SessionStatus {
  const normalized = status.trim().toLowerCase();
  if (status === "已同步" || normalized === "completed" || normalized === "done" || normalized === "success") return "已同步";
  if (status === "进行中" || normalized === "running" || normalized === "processing" || normalized === "queued") return "进行中";
  if (status.includes("失败") || normalized === "failed" || normalized === "error" || normalized === "cancelled") return "待处理";
  if (status === "草稿" || status === "待处理") return status;
  return "进行中";
}

function mapKind(session: SyncSession): Pick<SessionItem, "kind" | "kindLabel"> {
  const signal = (session.artifact?.kind || session.artifact?.intent || session.intent || "").trim().toLowerCase();
  if (signal === "board") return { kind: "canvas", kindLabel: "画布" };
  if (signal === "ppt" || signal === "docx" || signal === "presentation") return { kind: "doc", kindLabel: "文稿" };
  return { kind: "chat", kindLabel: "聊天" };
}

function formatUpdatedAt(timestamp: string): string {
  const parsed = Date.parse(timestamp);
  if (Number.isNaN(parsed)) return "刚刚";
  const date = new Date(parsed);
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

function isSameDay(left: Date, right: Date): boolean {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function isYesterday(date: Date, today: Date): boolean {
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  return isSameDay(date, yesterday);
}

function getSectionTitle(timestamp: string, now = new Date()): string {
  const parsed = Date.parse(timestamp);
  if (Number.isNaN(parsed)) return "今天";
  const date = new Date(parsed);
  if (isSameDay(date, now)) return "今天";
  if (isYesterday(date, now)) return "昨天";
  const weekAgo = new Date(now);
  weekAgo.setDate(now.getDate() - 7);
  if (date >= weekAgo) return "本周更早";
  return "更早";
}

function makeParticipant(): SessionParticipant {
  return { id: "eko-bot", name: "Eko Bot", initials: "EK" };
}

function makeSessionItem(session: SyncSession): SessionItem {
  const source = session.source === "feishu" ? "飞书" : "IM";
  const status = mapStatus(session.status);
  const updatedAt = formatUpdatedAt(session.updated_at);
  const participant = makeParticipant();
  const { kind, kindLabel } = mapKind(session);
  return {
    id: session.session_id,
    title: session.title || "未命名会话",
    summary: session.summary || "由飞书消息触发的新会话。",
    source,
    kind,
    kindLabel,
    status,
    updatedAt,
    participants: [participant],
    preview: {
      id: session.session_id,
      title: session.title || "未命名会话",
      source,
      startedAt: updatedAt,
      outputMode: kindLabel,
      status,
      syncedAt: updatedAt,
      summary: session.summary || "由飞书消息触发的新会话。",
      collaborators: [participant],
      relatedItems: [],
      activity: {
        id: `${session.session_id}:activity`,
        actor: "Eko Bot",
        action: "创建了新会话",
        time: "刚刚",
      },
      externalUrl:
        typeof session.artifact?.sharing_url === "string" && session.artifact.sharing_url
          ? session.artifact.sharing_url
          : undefined,
    },
  };
}

function groupSessions(sessions: SyncSession[]): SessionSection[] {
  const now = new Date();
  const ordered = [...sessions].sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at));
  const sectionMap = new Map<string, SessionItem[]>();

  for (const session of ordered) {
    const title = getSectionTitle(session.updated_at, now);
    const items = sectionMap.get(title) ?? [];
    items.push(makeSessionItem(session));
    sectionMap.set(title, items);
  }

  const sectionOrder = ["今天", "昨天", "本周更早", "更早"];
  return sectionOrder.flatMap((title) => {
    const items = sectionMap.get(title);
    return items && items.length > 0 ? [{ title, items }] : [];
  });
}

async function fetchSyncSessions(): Promise<SyncSession[]> {
  const origin = getBackendOrigin();
  try {
    const response = await fetch(`${origin}/api/v1/sync/sessions`, {
      cache: "no-store",
    });
    const body = (await response.json().catch(() => null)) as { code?: number; data?: SyncSession[] } | null;
    if (!response.ok || !body || body.code !== 0 || !Array.isArray(body.data)) {
      return [];
    }
    return body.data;
  } catch {
    return [];
  }
}

export async function getSessionListPageData(): Promise<SessionListPageData> {
  const sessions = await fetchSyncSessions();
  return {
    teamName: "Eko 工作区",
    teamMembersLabel: sessions.length > 0 ? `${sessions.length} 个会话` : "暂无会话",
    user: {
      name: "Eko User",
      email: "eko.user@eko.ai",
      initials: "EU",
    },
    sections: groupSessions(sessions),
  };
}
