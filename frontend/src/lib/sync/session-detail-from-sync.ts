import type { HeaderBadge } from "@/types/workspace";
import type {
  DetailActivity,
  DetailCanvasNode,
  DetailEvidenceItem,
  DetailMessage,
  DetailNavItem,
  DetailOutputTab,
  DetailRelatedFile,
  DetailSourceItem,
  DetailSyncAction,
  SessionDetailData,
} from "@/types/session-detail";

import type { SyncSession } from "./fetch-session";

type SyncSessionMessage = {
  role: string;
  content: string;
  timestamp?: number | null;
  sender_open_id?: string | null;
  sender_union_id?: string | null;
  sender_name?: string | null;
  platform_user_id?: string | null;
  platform_display_name?: string | null;
  avatar_url?: string | null;
};

type SyncSessionArtifact = {
  kind?: string | null;
  intent?: string | null;
  title?: string | null;
  job_id?: string | null;
  status?: string | null;
  progress?: number | null;
  current_step?: string | null;
  download_url?: string | null;
  error_message?: string | null;
  content?: string | null;
  sharing_url?: string | null;
  whiteboard_id?: string | null;
  preview_url?: string | null;
  result_summary?: string | null;
};

const navItems: DetailNavItem[] = [
  { id: "home", label: "主页", icon: "home" },
  { id: "chat", label: "会话", icon: "chat", active: true },
  { id: "doc", label: "文档", icon: "doc" },
  { id: "share", label: "分享 / 协作", icon: "share" },
  { id: "task", label: "任务", icon: "task" },
  { id: "team", label: "团队", icon: "team" },
  { id: "apps", label: "应用", icon: "apps" },
  { id: "settings", label: "设置", icon: "settings" },
];

const outputTabs: DetailOutputTab[] = [
  { key: "chat", label: "聊天", accent: "chat" },
  { key: "doc", label: "文稿", accent: "doc" },
  { key: "canvas", label: "画布", accent: "canvas" },
];

function statusBadge(status: string): HeaderBadge {
  if (status.includes("失败")) return { label: "失败", tone: "neutral" };
  if (status === "已同步" || status === "completed" || status === "done") return { label: status === "已同步" ? status : "已完成", tone: "success" };
  return { label: status || "进行中", tone: "info" };
}

function formatTimeLabel(timestamp: string): string {
  const parsed = Date.parse(timestamp);
  if (Number.isNaN(parsed)) return "刚刚";
  const date = new Date(parsed);
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

function formatMessageTime(timestamp?: number | null): string {
  if (timestamp == null) return "刚刚";
  const normalized = timestamp < 1e12 ? timestamp * 1000 : timestamp;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return "刚刚";
  const hh = date.getHours().toString().padStart(2, "0");
  const mm = date.getMinutes().toString().padStart(2, "0");
  return `${hh}:${mm}`;
}

function normalizeSignal(value?: string | null): string {
  return (value ?? "").trim().toLowerCase();
}

function splitMarkdownSections(markdown?: string | null): SessionDetailData["document"]["sections"] {
  const source = (markdown ?? "").trim();
  if (!source) return [];

  const lines = source.split(/\r?\n/);
  const sections: SessionDetailData["document"]["sections"] = [];
  let currentTitle = "正文";
  let buffer: string[] = [];

  const flush = () => {
    const body = buffer.join("\n").trim();
    if (!body && sections.length > 0) return;
    sections.push({ title: currentTitle, body: body || "待补充内容" });
    buffer = [];
  };

  for (const line of lines) {
    const heading = line.match(/^#{1,3}\s+(.+)$/);
    if (heading) {
      if (buffer.length > 0) flush();
      currentTitle = heading[1].trim();
      continue;
    }
    buffer.push(line);
  }

  if (buffer.length > 0 || sections.length === 0) flush();
  return sections.filter((section) => (section.body ?? "").trim().length > 0 || section.title.trim().length > 0);
}

function resolveDefaultTab(session: SyncSession): "chat" | "doc" | "canvas" {
  const artifactKind = normalizeSignal(session.artifact?.kind);
  const intent = normalizeSignal(session.artifact?.intent ?? session.intent);

  if (artifactKind === "board" || intent === "board") return "canvas";
  if (artifactKind === "ppt" || artifactKind === "docx" || intent === "ppt" || intent === "docx" || intent === "presentation") {
    return "doc";
  }
  return "chat";
}

function resolveLayoutVariant(defaultTab: "chat" | "doc" | "canvas"): "chat" | "doc" | "canvas" {
  return defaultTab;
}

function buildMessageEntries(messages: SyncSessionMessage[]): DetailMessage[] {
  const normalizedMessages: SyncSessionMessage[] = [];
  for (const message of messages) {
    const role = normalizeSignal(message.role);
    const isEko = role === "eko" || role === "assistant" || role === "bot" || role === "system";
    const isUser = role === "user" || role === "member";
    if (isUser) {
      const content = message.content.trim();
      const duplicateUserIndexes = normalizedMessages
        .map((item, index) => {
          const itemRole = normalizeSignal(item.role);
          return (itemRole === "user" || itemRole === "member") && item.content.trim() === content ? index : -1;
        })
        .filter((index) => index >= 0);
      if (duplicateUserIndexes.length > 0) {
        let duplicateUserIndex = duplicateUserIndexes[duplicateUserIndexes.length - 1];
        for (let cursor = duplicateUserIndexes.length - 2; cursor >= 0; cursor -= 1) {
          const previousIndex = duplicateUserIndexes[cursor];
          const sameTurnTail = normalizedMessages.slice(previousIndex + 1, duplicateUserIndex).every((item) => {
            const itemRole = normalizeSignal(item.role);
            return itemRole === "eko" || itemRole === "assistant" || itemRole === "bot" || itemRole === "system";
          });
          if (!sameTurnTail) break;
          duplicateUserIndex = previousIndex;
        }
        const repeatedTurnTail = normalizedMessages
          .slice(duplicateUserIndex + 1)
          .every((item) => {
            const itemRole = normalizeSignal(item.role);
            return itemRole === "eko" || itemRole === "assistant" || itemRole === "bot" || itemRole === "system";
          });
        if (repeatedTurnTail) {
          normalizedMessages.splice(duplicateUserIndex + 1);
          continue;
        }
      }
    }
    const previous = normalizedMessages[normalizedMessages.length - 1];
    const previousRole = normalizeSignal(previous?.role);
    const previousIsEko = previousRole === "eko" || previousRole === "assistant" || previousRole === "bot" || previousRole === "system";
    if (isEko && previous && previousIsEko) {
      const nextContent = message.content.trim();
      const previousContent = previous.content.trim();
      if (!nextContent || previousContent.includes(nextContent)) continue;
      if (nextContent.includes(previousContent)) {
        previous.content = nextContent;
      } else {
        previous.content = `${previousContent}\n\n${nextContent}`;
      }
      continue;
    }
    normalizedMessages.push({ ...message });
  }

  return normalizedMessages.map((message, index) => {
    const role = normalizeSignal(message.role);
    const isEko = role === "eko" || role === "assistant" || role === "bot" || role === "system";
    const author = isEko ? "Eko" : message.platform_display_name || message.sender_name || "成员";
    return {
      id: `msg-${index}`,
      author,
      role: isEko ? "eko" : "member",
      time: formatMessageTime(message.timestamp),
      body: message.content,
      avatar: isEko ? "E" : author.slice(0, 1).toUpperCase(),
      sent: true,
    };
  });
}

function buildMessages(session: SyncSession): DetailMessage[] {
  if (session.messages && session.messages.length > 0) {
    return buildMessageEntries(session.messages);
  }

  const body = session.summary || "收到飞书群聊消息，正在拉取上下文并建立会话。";
  const messages: DetailMessage[] = [];
  if (session.instruction?.trim()) {
    const triggerMessage = session.messages?.find((message) => normalizeSignal(message.role) === "user");
    const author = triggerMessage?.platform_display_name || triggerMessage?.sender_name || "成员";
    messages.push({
      id: `${session.session_id}:trigger`,
      author,
      role: "member",
      time: formatMessageTime(triggerMessage?.timestamp),
      body: session.instruction.trim(),
      avatar: author.slice(0, 1).toUpperCase(),
      sent: true,
      mention: "@Eko_Test",
    });
  }

  messages.push(
    {
      id: `${session.session_id}:system`,
      author: "Eko",
      role: "eko",
      time: "刚刚",
      body,
      avatar: "E",
      sent: true,
    },
  );
  return messages;
}

function buildSourceEvidence(session: SyncSession): DetailEvidenceItem[] {
  return [
    { id: `${session.session_id}:source`, title: "飞书群聊事件", description: "由 @机器人 message 触发的新会话。", tone: "chat" },
  ];
}

function buildSources(session: SyncSession): DetailSourceItem[] {
  const contextSize = session.context_size ?? 0;
  return [
    { id: `${session.session_id}:ctx`, title: "最近群聊上下文", description: `已读取 ${contextSize} 条相关消息。`, status: "completed" },
  ];
}

function buildActivities(session: SyncSession): DetailActivity[] {
  return [
    { id: `${session.session_id}:open`, title: "会话已创建", time: "刚刚", tone: "session" },
    { id: `${session.session_id}:ctx`, title: "上下文读取完成", time: "刚刚", tone: "data" },
  ];
}

function buildRelatedFiles(session: SyncSession): DetailRelatedFile[] {
  return [
    { id: `${session.session_id}:note`, title: "会话摘要", updatedAt: formatTimeLabel(session.updated_at), tone: "doc" },
  ];
}

function buildSyncActions(session: SyncSession): DetailSyncAction[] {
  const completed = session.status === "已同步" || session.status === "completed" || session.status === "done";
  return [
    {
      id: `${session.session_id}:sync`,
      title: "回传飞书",
      status: session.status.includes("失败") ? "warning" : completed ? "completed" : "running",
    },
  ];
}

function buildArtifact(session: SyncSession): SyncSessionArtifact | null {
  const artifact = session.artifact;
  const hasArtifactSignal = Boolean(
    artifact?.kind ||
      artifact?.job_id ||
      artifact?.download_url ||
      artifact?.content ||
      artifact?.sharing_url ||
      artifact?.whiteboard_id ||
      artifact?.preview_url ||
      artifact?.result_summary ||
      artifact?.error_message,
  );
  if (!hasArtifactSignal) return null;

  const artifactKind = normalizeSignal(artifact?.kind);
  const intent = normalizeSignal(artifact?.intent ?? session.intent);
  const kind =
    artifactKind === "ppt" || artifactKind === "docx" || artifactKind === "board"
      ? artifactKind
      : intent === "ppt" || intent === "docx" || intent === "board"
        ? intent
        : "";

  if (!kind) return null;

  const content =
    typeof artifact?.content === "string" && artifact.content.trim().length > 0
      ? artifact.content
      : null;
  const sessionDone = session.status === "completed" || session.status === "已同步" || session.status === "done";
  const sessionFailed = session.status === "failed" || session.status.includes("失败");

  return {
    kind,
    intent: (artifact?.intent as string | null | undefined) ?? session.intent ?? null,
    title: typeof artifact?.title === "string" ? artifact.title : session.title,
    job_id: typeof artifact?.job_id === "string" ? artifact.job_id : null,
    status: typeof artifact?.status === "string" ? artifact.status : sessionDone ? "completed" : sessionFailed ? "failed" : null,
    progress: typeof artifact?.progress === "number" ? artifact.progress : null,
    current_step: typeof artifact?.current_step === "string" ? artifact.current_step : null,
    download_url: typeof artifact?.download_url === "string" ? artifact.download_url : null,
    error_message: typeof artifact?.error_message === "string" ? artifact.error_message : null,
    content,
    sharing_url: typeof artifact?.sharing_url === "string" ? artifact.sharing_url : null,
    whiteboard_id: typeof artifact?.whiteboard_id === "string" ? artifact.whiteboard_id : null,
    preview_url: typeof artifact?.preview_url === "string" ? artifact.preview_url : null,
    result_summary: typeof artifact?.result_summary === "string" ? artifact.result_summary : null,
  };
}

function buildCanvasNodes(): DetailCanvasNode[] {
  return [
    { id: "n1", index: 1, title: "消息触发", bullets: ["@机器人", "message"], icon: "rocket" },
    { id: "n2", index: 2, title: "上下文提取", bullets: ["近期群聊", "语义窗口"], icon: "trend" },
    { id: "n3", index: 3, title: "结果回写", bullets: ["WS 事件", "会话目录"], icon: "check" },
  ];
}

export function buildSessionDetailData(session: SyncSession): SessionDetailData {
  const contextSize = session.context_size ?? 0;
  const badges = [statusBadge(session.source === "feishu" ? "飞书" : "IM"), statusBadge(session.status)] as HeaderBadge[];
  const sessionCompleted = session.status === "已同步" || session.status === "completed" || session.status === "done";
  const defaultTab = resolveDefaultTab(session);
  const artifact = buildArtifact(session);
  const markdown = artifact?.kind === "docx" ? artifact.content ?? session.summary : session.summary;
  const documentSections =
    artifact?.kind === "docx"
      ? splitMarkdownSections(markdown)
      : [{ title: "摘要", body: session.summary }];

  return {
    id: session.session_id,
    layoutVariant: resolveLayoutVariant(defaultTab),
    title: session.title,
    breadcrumb: ["Eko", "会话", session.title],
    topBadges: badges,
    navItems,
    assistantName: "Eko",
    assistantEmail: session.status,
    conversationTitle: "对话",
    messages: buildMessages(session),
    missionTitle: session.title,
    missionBadges: [session.source === "feishu" ? "飞书" : "IM", "聊天", session.status],
    missionSubtitle: session.summary,
    confidence: contextSize > 0 ? "已获取上下文" : "暂无上下文",
    contextQuality: contextSize > 0 ? "高" : "低",
    workflow: [
      { id: "1", title: "创建会话", status: "completed" },
      { id: "2", title: "读取上下文", status: contextSize > 0 || sessionCompleted ? "completed" : "running" },
      { id: "3", title: "生成回复", status: session.status.includes("失败") ? "warning" : sessionCompleted ? "completed" : "running" },
      { id: "4", title: "同步结果", status: sessionCompleted ? "completed" : "pending" },
    ],
    outputTabs,
    defaultTab,
    chatReply: {
      title: "会话摘要",
      body: session.summary,
      source: `来源：${session.source === "feishu" ? "飞书群聊" : "IM"} · ${formatTimeLabel(session.updated_at)}`,
    },
    document: {
      title: artifact?.kind === "ppt" ? "PPT 预览" : artifact?.kind === "docx" ? "文档预览" : "文稿视图",
      date: formatTimeLabel(session.updated_at),
      markdown,
      sections: documentSections,
      artifact: artifact
        ? {
            kind: artifact.kind ?? undefined,
            intent: artifact.intent ?? null,
            title: artifact.title ?? session.title,
            jobId: artifact.job_id ?? null,
            status: artifact.status ?? null,
            progress: artifact.progress ?? null,
            currentStep: artifact.current_step ?? null,
            downloadUrl: artifact.download_url ?? null,
            errorMessage: artifact.error_message ?? null,
            content: artifact.content ?? null,
            sharingUrl: artifact.sharing_url ?? null,
            whiteboardId: artifact.whiteboard_id ?? null,
            previewUrl: artifact.preview_url ?? null,
            resultSummary: artifact.result_summary ?? null,
          }
        : undefined,
    },
    canvas: {
      title: artifact?.kind === "board" ? "画板预览" : "画布视图",
      nodes: buildCanvasNodes(),
      artifact:
        artifact?.kind === "board"
          ? {
              kind: artifact.kind ?? undefined,
              intent: artifact.intent ?? null,
              title: artifact.title ?? session.title,
              status: artifact.status ?? null,
              progress: artifact.progress ?? null,
              currentStep: artifact.current_step ?? null,
              errorMessage: artifact.error_message ?? null,
              sharingUrl: artifact.sharing_url ?? null,
              whiteboardId: artifact.whiteboard_id ?? null,
              previewUrl: artifact.preview_url ?? null,
              resultSummary: artifact.result_summary ?? null,
            }
          : undefined,
    },
    artifact: artifact
      ? {
          kind: artifact.kind ?? undefined,
          intent: artifact.intent ?? null,
          title: artifact.title ?? session.title,
          jobId: artifact.job_id ?? null,
          status: artifact.status ?? null,
          progress: artifact.progress ?? null,
          currentStep: artifact.current_step ?? null,
          downloadUrl: artifact.download_url ?? null,
          errorMessage: artifact.error_message ?? null,
          content: artifact.content ?? null,
          sharingUrl: artifact.sharing_url ?? null,
          whiteboardId: artifact.whiteboard_id ?? null,
          previewUrl: artifact.preview_url ?? null,
          resultSummary: artifact.result_summary ?? null,
        }
      : undefined,
    intent: session.intent ?? artifact?.intent ?? null,
    disabledCards: [],
    contextSources: buildSources(session),
    contextMessages: session.context_messages ?? [],
    instruction: session.instruction ?? null,
    sourceEvidence: buildSourceEvidence(session),
    syncActions: buildSyncActions(session),
    statusBadges: badges,
    systemNote: "当前展示的是后端真实会话数据，没有 mock 兜底。",
    actionButtons: ["分享", "导出"],
    workflowCards: [
      { id: `${session.session_id}:wf-1`, title: "会话创建", status: "completed", subtitle: "后端已登记", timestamp: "刚刚" },
      {
        id: `${session.session_id}:wf-2`,
        title: "上下文提取",
        status: contextSize > 0 ? "completed" : "running",
        subtitle: contextSize > 0 ? `已读取 ${contextSize} 条` : "等待上下文",
      },
      { id: `${session.session_id}:wf-3`, title: "结果同步", status: sessionCompleted ? "completed" : "pending" },
    ],
    progress: session.status === "已同步" ? 1 : 0.5,
    relatedFiles: buildRelatedFiles(session),
    memoryNote: {
      title: "会话记忆",
      body: "会话信息来自后端实时登记，不再依赖静态示例数据。",
      action: "查看详情",
    },
    syncOverview: {
      statusLabel: session.status,
      items: [session.summary],
    },
    activities: buildActivities(session),
  };
}
