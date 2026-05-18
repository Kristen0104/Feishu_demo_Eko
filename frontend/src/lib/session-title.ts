type SessionTitleMessage = {
  role?: string | null;
  content?: string | null;
};

type SessionTitleArtifact = {
  kind?: string | null;
  intent?: string | null;
  title?: string | null;
  result_summary?: string | null;
  current_step?: string | null;
};

export type SessionTitleSource = {
  session_id?: string | null;
  source?: string | null;
  title?: string | null;
  summary?: string | null;
  instruction?: string | null;
  updated_at?: string | null;
  opened_at?: string | null;
  intent?: string | null;
  artifact?: SessionTitleArtifact | null;
  messages?: SessionTitleMessage[] | null;
  context_messages?: SessionTitleMessage[] | null;
};

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function looksLikeTechnicalSessionTitle(value?: string | null): boolean {
  const raw = (value ?? "").trim();
  if (!raw) return false;
  const decoded = safeDecode(raw);
  const normalized = decoded.toLowerCase();
  if (/^feishu:[^ ]{20,}$/.test(normalized)) return true;
  if (/^feishu%3a/i.test(raw)) return true;
  if (/%3a/i.test(raw) && raw.length > 24) return true;
  if (/(^|:)o[cm]_[a-z0-9]{16,}/i.test(decoded)) return true;
  if (/^[a-z][a-z0-9_-]*:[^ ]{24,}$/i.test(decoded)) return true;
  if (/^[a-z0-9_-]{48,}$/i.test(decoded)) return true;
  return raw.length > 56 && !/[\u4e00-\u9fff]/.test(raw) && /[_:%-]/.test(raw);
}

function normalizeText(value?: string | null): string {
  return (value ?? "")
    .replace(/\r/g, "\n")
    .replace(/\s+/g, " ")
    .trim();
}

function removeRobotMention(value: string): string {
  return value
    .replace(/^(@[\w\u4e00-\u9fff.-]+\s*)+/i, "")
    .replace(/^(Eko_Test|Eko|机器人)[，,：:\s]+/i, "")
    .trim();
}

function isLowValueCandidate(value: string): boolean {
  const normalized = value.replace(/\s+/g, "");
  if (!normalized) return true;
  if (looksLikeTechnicalSessionTitle(value)) return true;
  if (normalized === "未命名会话" || normalized === "新会话") return true;
  if (normalized.includes("由飞书消息触发的新会话")) return true;
  if (normalized.includes("正在加载真实会话数据")) return true;
  if (normalized.includes("文档生成完成") || normalized.includes("处理已完成")) return true;
  if (normalized.includes("已同步到飞书") && normalized.length < 24) return true;
  if (normalized.includes("规划已更新")) return true;
  return false;
}

function compactTaskText(value?: string | null): string | null {
  let text = removeRobotMention(normalizeText(value));
  if (!text || isLowValueCandidate(text)) return null;

  text = text
    .replace(/^使用\s*(docx|ppt|board|画板|文档|演示文稿)\s*(工具|能力)?\s*/iu, "")
    .replace(/^(请|请你|帮我|帮忙|麻烦|麻烦你|给我)\s*/u, "")
    .replace(/^(生成|创建|制作|整理|输出|写|做)\s*(一份|一个|一下|份|个)?\s*/u, "")
    .replace(/^(文档生成|PPT生成|画板生成)\s*/iu, "")
    .replace(/[，,。.\s]*(约|大约)?\d+\s*(个)?字(左右)?$/u, "")
    .replace(/[，,。.\s]*(约|大约)?\d+\s*(页|张|屏)(左右)?$/u, "")
    .replace(/[，,。.\s]*(谢谢|辛苦了)$/u, "")
    .trim();

  text = text
    .replace(/^使用\s*(docx|ppt|board|画板|文档|演示文稿)\s*(工具|能力)?\s*/iu, "")
    .replace(/^(生成|创建|制作|整理|输出|写|做)\s*(一份|一个|一下|份|个)?\s*/u, "")
    .replace(/^(约|大约)?\d+\s*(个)?字(左右)?的?/u, "")
    .replace(/^(约|大约)?\d+\s*(页|张|屏)(左右)?的?/u, "")
    .trim();

  if (!text || isLowValueCandidate(text)) return null;
  return text;
}

function firstUserMessage(messages?: SessionTitleMessage[] | null): string | null {
  const list = Array.isArray(messages) ? messages : [];
  const found = list.find((message) => {
    const role = (message.role ?? "").trim().toLowerCase();
    return role === "user" || role === "member";
  });
  return found?.content ?? null;
}

function displayKind(session: SessionTitleSource): string {
  const signal = (session.artifact?.kind || session.artifact?.intent || session.intent || "").trim().toLowerCase();
  if (signal === "ppt" || signal === "presentation") return "PPT";
  if (signal === "docx") return "文档";
  if (signal === "board") return "画板";
  return "会话";
}

function displaySource(session: SessionTitleSource): string {
  return (session.source ?? "").trim().toLowerCase() === "feishu" ? "飞书" : "IM";
}

function displayDate(session: SessionTitleSource): string | null {
  const parsed = Date.parse(session.updated_at || session.opened_at || "");
  if (Number.isNaN(parsed)) return null;
  const date = new Date(parsed);
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}

function shorten(value: string, maxLength = 32): string {
  const chars = Array.from(value);
  if (chars.length <= maxLength) return value;
  return `${chars.slice(0, maxLength).join("")}...`;
}

export function getReadableSessionTitle(session: SessionTitleSource): string {
  const candidates = [
    session.instruction,
    firstUserMessage(session.messages),
    session.title,
    session.artifact?.title,
    firstUserMessage(session.context_messages),
    session.summary,
    session.artifact?.result_summary,
    session.artifact?.current_step,
  ];

  for (const candidate of candidates) {
    const compacted = compactTaskText(candidate);
    if (compacted) return shorten(compacted);
  }

  const date = displayDate(session);
  return [displaySource(session), displayKind(session), date].filter(Boolean).join(" · ");
}
