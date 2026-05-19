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

import { getReadableSessionTitle } from "@/lib/session-title";
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
  bitable_archive_results?: BitableArchiveResult[] | null;
};

type BitableArchiveResult = {
  source_id?: string | null;
  record_id?: string | null;
  record_url?: string | null;
  status?: string | null;
  message?: string | null;
  error?: string | null;
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

function isCompletedStatus(status?: string | null): boolean {
  const normalized = normalizeSignal(status);
  return status === "已同步" || status === "已完成" || normalized === "completed" || normalized === "done" || normalized === "success";
}

function isFailedStatus(status?: string | null): boolean {
  const normalized = normalizeSignal(status);
  return normalized === "failed" || (status ?? "").includes("失败");
}

function hasArtifactOutput(session: SyncSession): boolean {
  const artifact = session.artifact;
  if (!artifact || isFailedStatus(session.status) || isFailedStatus(artifact.status)) return false;
  return Boolean(
    artifact.content ||
      artifact.download_url ||
      artifact.sharing_url ||
      artifact.whiteboard_id ||
      artifact.preview_url ||
      artifact.result_summary ||
      (artifact.job_id && isCompletedStatus(session.status)),
  );
}

function looksLikeClarificationPrompt(content: string): boolean {
  const normalized = content.replace(/\s+/g, "");
  const asking = normalized.includes("请问") || normalized.includes("需要") || normalized.includes("希望") || normalized.includes("补充");
  const aboutRequirements = normalized.includes("文档") || normalized.includes("PPT") || normalized.includes("内容") || normalized.includes("需求");
  const asksForDetails = normalized.includes("哪些") || normalized.includes("具体") || normalized.includes("包含") || normalized.includes("补充");
  return asking && aboutRequirements && asksForDetails;
}

function looksCompletedMessage(content: string): boolean {
  const normalized = content.replace(/\s+/g, "");
  return (
    normalized.includes("已生成") ||
    normalized.includes("已经完成") ||
    normalized.includes("已完成") ||
    normalized.includes("生成完成") ||
    normalized.includes("可在右侧")
  );
}

function looksLikeInternalTraceMessage(content: string): boolean {
  const normalized = content.replace(/\s+/g, "");
  return (
    /走(?:chat|docx|ppt|board)?能力/i.test(normalized) ||
    /(?:chat|docx|ppt|board)能力/i.test(normalized) ||
    normalized.includes("意图已识别") ||
    normalized.includes("规划已更新")
  );
}

function isClarificationAssistantMessage(content: string): boolean {
  const normalized = content.replace(/\s+/g, "");
  return (
    normalized.includes("你是想直接讨论") ||
    normalized.includes("还是生成一份文档") ||
    normalized.includes("执行前还需要确认") ||
    normalized.includes("请确认你希望我执行哪种动作")
  );
}

function compactInternalTraceMessage(content: string): string {
  if (!looksLikeInternalTraceMessage(content)) return content;
  const chunks = content
    .replace(/\r/g, "\n")
    .split(/\n{1,}|\s{2,}/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
  const completion = [...chunks].reverse().find((chunk) => looksCompletedMessage(chunk) || chunk.includes("同步到飞书"));
  if (completion) return completion;
  return "正在处理，会在右侧同步结果。";
}

function isBoardSession(session: SyncSession): boolean {
  const artifactKind = normalizeSignal(session.artifact?.kind);
  const intent = normalizeSignal(session.artifact?.intent ?? session.intent);
  return artifactKind === "board" || intent === "board";
}

function syncStatusLabel(status?: string | null): string {
  if (isFailedStatus(status)) return "失败";
  if (isCompletedStatus(status)) return "已完成";
  const normalized = normalizeSignal(status);
  if (normalized === "running" || normalized === "processing" || normalized === "queued" || status === "进行中") return "进行中";
  return status?.trim() || "进行中";
}

function buildSyncOverview(session: SyncSession, artifact: ReturnType<typeof buildArtifact>): SessionDetailData["syncOverview"] {
  if (!artifact || (artifact.kind !== "docx" && artifact.kind !== "ppt" && artifact.kind !== "board")) return undefined;

  const items = [
    artifact.result_summary,
    artifact.sharing_url ? "飞书链接已生成。" : null,
    artifact.download_url ? "下载文件已生成。" : null,
    artifact.whiteboard_id ? "画板内容已写入飞书。" : null,
  ].filter((item): item is string => typeof item === "string" && item.trim().length > 0);

  return {
    statusLabel: syncStatusLabel(artifact.status ?? session.status),
    items: items.length > 0 ? items : ["产物状态已同步到工作台。"],
  };
}

function compactMessageEntries(session: SyncSession, messages: DetailMessage[]): DetailMessage[] {
  const compacted = messages.map((message) =>
    message.role === "eko" ? { ...message, body: compactInternalTraceMessage(message.body) } : message,
  );
  return compacted.filter((message, index) => {
    if (message.role !== "eko") return true;
    if (isBoardSession(session) && looksLikeInternalTraceMessage(message.body)) return false;
    if (looksLikeClarificationPrompt(message.body)) {
      return !compacted.slice(index + 1).some((next) => next.role === "eko" && looksCompletedMessage(next.body));
    }
    if (message.body.includes("文档已生成，右侧可以查看") || message.body.includes("右侧可以查看、下载或继续编辑")) {
      return !compacted.slice(0, index).some((prev) => prev.role === "eko" && looksCompletedMessage(prev.body));
    }
    const previous = compacted[index - 1];
    return !(previous?.role === "eko" && previous.body.trim() === message.body.trim());
  });
}

function artifactReadyMessage(session: SyncSession): DetailMessage {
  const kind = normalizeSignal(session.artifact?.kind ?? session.intent);
  const body =
    kind === "ppt"
      ? "PPT 已生成，右侧可以预览和下载。"
      : kind === "board"
        ? "画板已生成，右侧可以打开查看。"
        : kind === "docx"
          ? "文档已生成，右侧可以查看、下载或继续编辑。"
          : "处理已完成，右侧可以查看结果。";
  return {
    id: `${session.session_id}:artifact-ready`,
    author: "Eko",
    role: "eko",
    time: "刚刚",
    body,
    avatar: "E",
    sent: true,
  };
}

function reconcileCompletedArtifactMessages(session: SyncSession, messages: DetailMessage[]): DetailMessage[] {
  if (!hasArtifactOutput(session)) return compactMessageEntries(session, messages);

  const next = compactMessageEntries(session, messages);
  while (next.length > 0) {
    const last = next[next.length - 1];
    if (last.role !== "eko" || !looksLikeClarificationPrompt(last.body)) break;
    next.pop();
  }

  const lastEko = [...next].reverse().find((message) => message.role === "eko");
  if (!lastEko || !looksCompletedMessage(lastEko.body)) {
    next.push(artifactReadyMessage(session));
  }
  return next;
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
      } else if (isClarificationAssistantMessage(previousContent) || isClarificationAssistantMessage(nextContent)) {
        previous.content = isClarificationAssistantMessage(previousContent) ? previousContent : nextContent;
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
    return reconcileCompletedArtifactMessages(session, buildMessageEntries(session.messages));
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
  return reconcileCompletedArtifactMessages(session, messages);
}

function buildSourceEvidence(session: SyncSession): DetailEvidenceItem[] {
  const evidence: DetailEvidenceItem[] = [
    { id: `${session.session_id}:source`, title: "飞书群聊事件", description: "由 @机器人 message 触发的新会话。", tone: "chat" },
  ];
  const archives = Array.isArray(session.artifact?.bitable_archive_results) ? session.artifact.bitable_archive_results : [];
  for (const item of archives) {
    evidence.push({
      id: `${session.session_id}:bitable:${item.source_id || item.record_id || evidence.length}`,
      title: "Bitable 归档",
      description: item.message || item.record_url || item.record_id || "生成产物已尝试归档到 Bitable。",
      tone: "record",
    });
  }
  return evidence;
}

function buildSources(session: SyncSession): DetailSourceItem[] {
  const contextSize = session.context_size ?? 0;
  const sources: DetailSourceItem[] = [
    { id: `${session.session_id}:ctx`, title: "最近群聊上下文", description: `已读取 ${contextSize} 条相关消息。`, status: "completed" },
  ];
  const archives = Array.isArray(session.artifact?.bitable_archive_results) ? session.artifact.bitable_archive_results : [];
  for (const item of archives) {
    sources.push({
      id: `${session.session_id}:archive:${item.source_id || item.record_id || sources.length}`,
      title: "Bitable 数据",
      description: item.status === "failed" ? item.error || item.message || "归档失败，主任务未中断。" : item.record_url || item.message || "已归档生成产物。",
      status: item.status === "failed" ? "warning" : "completed",
    });
  }
  return sources;
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
  const completed = isCompletedStatus(session.status);
  const actions: DetailSyncAction[] = [
    {
      id: `${session.session_id}:sync`,
      title: "回传飞书",
      status: session.status.includes("失败") ? "warning" : completed ? "completed" : "running",
    },
  ];
  const archives = Array.isArray(session.artifact?.bitable_archive_results) ? session.artifact.bitable_archive_results : [];
  for (const item of archives) {
    actions.push({
      id: `${session.session_id}:bitable-sync:${item.source_id || item.record_id || actions.length}`,
      title: item.status === "failed" ? "Bitable 归档失败" : "归档 Bitable",
      status: item.status === "failed" ? "warning" : "completed",
    });
  }
  return actions;
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
  const sessionDone = isCompletedStatus(session.status);
  const sessionFailed = isFailedStatus(session.status);
  const rawArtifactStatus = typeof artifact?.status === "string" ? artifact.status : null;
  const artifactFailed = isFailedStatus(rawArtifactStatus);

  return {
    kind,
    intent: (artifact?.intent as string | null | undefined) ?? session.intent ?? null,
    title: typeof artifact?.title === "string" ? artifact.title : getReadableSessionTitle(session),
    job_id: typeof artifact?.job_id === "string" ? artifact.job_id : null,
    status: artifactFailed ? rawArtifactStatus : sessionDone ? "completed" : rawArtifactStatus ?? (sessionFailed ? "failed" : null),
    progress: typeof artifact?.progress === "number" ? artifact.progress : null,
    current_step: typeof artifact?.current_step === "string" ? artifact.current_step : null,
    download_url: typeof artifact?.download_url === "string" ? artifact.download_url : null,
    error_message: typeof artifact?.error_message === "string" ? artifact.error_message : null,
    content,
    sharing_url: typeof artifact?.sharing_url === "string" ? artifact.sharing_url : null,
    whiteboard_id: typeof artifact?.whiteboard_id === "string" ? artifact.whiteboard_id : null,
    preview_url: typeof artifact?.preview_url === "string" ? artifact.preview_url : null,
    result_summary: typeof artifact?.result_summary === "string" ? artifact.result_summary : null,
    bitable_archive_results: Array.isArray(artifact?.bitable_archive_results) ? artifact.bitable_archive_results as BitableArchiveResult[] : null,
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
  const sessionCompleted = isCompletedStatus(session.status);
  const defaultTab = resolveDefaultTab(session);
  const artifact = buildArtifact(session);
  const readableTitle = getReadableSessionTitle(session);
  const markdown = artifact?.kind === "docx" ? artifact.content ?? session.summary : session.summary;
  const documentSections =
    artifact?.kind === "docx"
      ? splitMarkdownSections(markdown)
      : [{ title: "摘要", body: session.summary }];

  return {
    id: session.session_id,
    layoutVariant: resolveLayoutVariant(defaultTab),
    title: readableTitle,
    breadcrumb: ["Eko", "会话", readableTitle],
    topBadges: badges,
    navItems,
    assistantName: "Eko",
    assistantEmail: session.status,
    conversationTitle: "对话",
    messages: buildMessages(session),
    missionTitle: readableTitle,
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
            title: artifact.title ?? readableTitle,
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
            bitableArchiveResults: artifact.bitable_archive_results ?? null,
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
              title: artifact.title ?? readableTitle,
              status: artifact.status ?? null,
              progress: artifact.progress ?? null,
              currentStep: artifact.current_step ?? null,
              errorMessage: artifact.error_message ?? null,
              sharingUrl: artifact.sharing_url ?? null,
              whiteboardId: artifact.whiteboard_id ?? null,
              previewUrl: artifact.preview_url ?? null,
              resultSummary: artifact.result_summary ?? null,
              bitableArchiveResults: artifact.bitable_archive_results ?? null,
            }
          : undefined,
    },
    artifact: artifact
      ? {
          kind: artifact.kind ?? undefined,
          intent: artifact.intent ?? null,
          title: artifact.title ?? readableTitle,
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
          bitableArchiveResults: artifact.bitable_archive_results ?? null,
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
    systemNote: "当前展示的是后端真实会话数据。",
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
    progress: sessionCompleted ? 1 : 0.5,
    relatedFiles: buildRelatedFiles(session),
    memoryNote: {
      title: "会话记忆",
      body: "会话信息来自后端实时登记。",
      action: "查看详情",
    },
    syncOverview: buildSyncOverview(session, artifact),
    activities: buildActivities(session),
  };
}
