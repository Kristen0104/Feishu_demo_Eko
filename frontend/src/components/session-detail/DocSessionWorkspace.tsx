"use client";

import Image from "next/image";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { MessageInput } from "@/components/MessageInput";
import { MoreIcon } from "@/components/Icons";
import { Stepper } from "@/components/Stepper";
import { EvidencePill, HeaderBadge, StatusPill } from "@/components/UiPrimitives";
import { useEkoSessionRealtime } from "@/hooks/useEkoSessionRealtime";
import { apiUrl, fetchEkoJson } from "@/lib/eko-api";
import { fetchSyncSession } from "@/lib/sync/fetch-session";
import { streamAgentChat, type AgentChatStreamEvent } from "@/lib/agent/sse-stream";
import { useAppStore } from "@/store/app-store";
import { useAgentRuntimeStore, type PlanningPlanWire, type PlanningStepWire, type RetrievedSourceWire } from "@/store/agent-runtime-store";
import {
  DetailActivity,
  DetailCanvasNode,
  DetailDocumentArtifact,
  DetailEvidenceItem,
  DetailRelatedFile,
  DetailSourceItem,
  DetailSyncAction,
  DetailTabKey,
  SessionDetailData,
} from "@/types/session-detail";
import type { WorkflowStatus } from "@/types/workspace";
import type { WorkflowStep } from "@/types/workspace";

import { useSessionWorkspaceSearch } from "@/components/workspace/session-workspace-search";
import { DetailConversationMessage } from "./DetailConversationMessage";
import { detailDesignTokens } from "./designTokens";

function SmallIcon({
  type,
  tone = "blue",
}: {
  type:
    | "doc"
    | "sheet"
    | "deck"
    | "memory"
    | "sync"
    | "filter"
    | "chat"
    | "route"
    | "data"
    | "session"
    | "search"
    | "share"
    | "download"
    | "spark"
    | "trend"
    | "rocket"
    | "calendar"
    | "alert"
    | "check";
  tone?: "blue" | "green" | "purple" | "orange" | "slate" | "red";
}) {
  const colors = {
    blue: "#2563EB",
    green: "#16A34A",
    purple: "#8B5CF6",
    orange: "#F59E0B",
    slate: "#64748B",
    red: "#EF4444",
  } as const;
  const stroke = colors[tone];

  if (type === "filter")
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M3.2 4H14.8L10.4 9.2V13.6L7.6 15V9.2L3.2 4Z" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    );
  if (type === "share")
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <circle cx="4.2" cy="9" r="1.8" stroke={stroke} strokeWidth="1.5" />
        <circle cx="13.8" cy="4.8" r="1.8" stroke={stroke} strokeWidth="1.5" />
        <circle cx="13.8" cy="13.2" r="1.8" stroke={stroke} strokeWidth="1.5" />
        <path d="M5.8 8.3L12 5.5" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        <path d="M5.8 9.7L12 12.5" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  if (type === "download")
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M9 3.3V10.4" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        <path d="M6.2 7.9L9 10.7L11.8 7.9" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M3.5 13.8H14.5" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  if (type === "sync")
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M4.5 7.1C4.9 5.3 6.6 4 8.6 4C10 4 11.3 4.6 12 5.6" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        <path d="M12.1 3.9V5.9H10.1" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M13.5 10.9C13.1 12.7 11.4 14 9.4 14C8 14 6.7 13.4 6 12.4" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        <path d="M5.9 14.1V12.1H7.9" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (type === "memory")
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M9 3.5C6.5 3.5 4.5 5.5 4.5 8C4.5 10.5 6.5 12.5 9 12.5C11.5 12.5 13.5 10.5 13.5 8C13.5 5.5 11.5 3.5 9 3.5Z" stroke={stroke} strokeWidth="1.5" />
        <path d="M9 1.8V3.5M9 12.5V16.2M16.2 8H13.5M4.5 8H1.8" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  if (type === "chat")
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <rect x="2.5" y="3.1" width="13" height="9.2" rx="2.8" stroke={stroke} strokeWidth="1.5" />
        <path d="M6.1 12.2L5.5 14.6L8.1 12.2" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (type === "session")
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <circle cx="9" cy="9" r="6.2" stroke={stroke} strokeWidth="1.5" />
        <circle cx="9" cy="9" r="1.8" fill={stroke} />
      </svg>
    );
  if (type === "trend")
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M3 16.2H17" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        <path d="M4.4 12.7L8.1 9.1L10.8 11.3L15.6 5.8" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12.8 5.8H15.6V8.6" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (type === "rocket")
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M11.2 4.1C13.4 4 15.1 4.9 16.1 5.9C16.1 8.7 15.2 11.1 13.2 13.1L9 9C10 7 11.1 5.5 11.2 4.1Z" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M8.7 9.4L6.2 9.8L4.2 11.8L5.8 8.3L8.7 9.4Z" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M10.6 11.3L11.7 14.2L8.2 15.8L10.2 13.8L10.6 11.3Z" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" />
        <circle cx="12.8" cy="7.1" r="1.2" stroke={stroke} strokeWidth="1.3" />
      </svg>
    );
  if (type === "calendar")
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <rect x="3" y="4.5" width="14" height="12" rx="2.5" stroke={stroke} strokeWidth="1.5" />
        <path d="M6.1 2.8V6.2M13.9 2.8V6.2M3 8.1H17" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        <path d="M7 11.6L9.1 13.6L13.4 9.3" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (type === "alert")
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M10 3.4L17 15.9H3L10 3.4Z" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M10 7.7V11.2" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="10" cy="13.9" r="0.8" fill={stroke} />
      </svg>
    );
  if (type === "check")
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="7.2" stroke={stroke} strokeWidth="1.5" />
        <path d="M6.5 10.1L8.8 12.4L13.7 7.5" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (type === "doc" || type === "sheet" || type === "deck") {
    const fileStroke = type === "deck" ? colors.purple : type === "sheet" ? colors.green : stroke;
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M4.2 2.6H10.2L13.8 6.2V15.4H4.2V2.6Z" stroke={fileStroke} strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M10 2.6V6.3H13.8" stroke={fileStroke} strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path d="M9 2.2L10.3 6.7L14.8 8L10.3 9.3L9 13.8L7.7 9.3L3.2 8L7.7 6.7L9 2.2Z" stroke={stroke} strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

function StageCard({
  title,
  subtitle,
  timestamp,
  status,
  highlighted,
}: {
  title: string;
  subtitle?: string;
  timestamp?: string;
  status: "completed" | "running" | "pending" | "warning";
  highlighted?: boolean;
}) {
  const badge = status === "completed" ? "已完成" : status === "running" ? "进行中" : status === "warning" ? "预警" : "待同步";
  const badgeClass =
    status === "completed"
      ? "bg-emerald-50 text-emerald-600"
      : status === "running"
        ? "bg-blue-50 text-blue-600"
        : status === "warning"
          ? "bg-amber-50 text-amber-600"
          : "bg-slate-100 text-slate-500";
  return (
    <div
      className={[
        "relative flex h-[76px] min-w-0 flex-col justify-between overflow-hidden rounded-[16px] border bg-white px-3 py-2 shadow-[0_8px_18px_rgba(148,163,184,0.05)]",
        highlighted ? "border-blue-400 shadow-[0_14px_24px_rgba(59,130,246,0.1)]" : "border-slate-200",
      ].join(" ")}
    >
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div
          className={[
            "flex h-8 w-8 items-center justify-center rounded-full border",
            status === "completed"
              ? "border-emerald-200 bg-emerald-50"
              : status === "running"
                ? "border-blue-200 bg-blue-50 shadow-[0_0_0_6px_rgba(59,130,246,0.06)]"
                : status === "warning"
                  ? "border-amber-200 bg-amber-50"
                  : "border-slate-200 bg-slate-50",
          ].join(" ")}
        >
          {status === "completed" ? (
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <circle cx="10" cy="10" r="8.4" stroke="#22C55E" strokeWidth="1.6" />
              <path d="M6.4 10.3L8.8 12.7L13.7 7.8" stroke="#22C55E" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : status === "running" ? (
            <div className="relative h-5 w-5">
              <span className="absolute inset-0 rounded-full border-[2px] border-blue-500 border-t-transparent animate-spin" />
            </div>
          ) : (
            <SmallIcon type="sync" tone={status === "warning" ? "orange" : "slate"} />
          )}
        </div>
        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] leading-4 font-semibold ${badgeClass}`}>{badge}</span>
      </div>
      <div>
        <p className="truncate text-[10px] font-semibold leading-4 text-slate-900">{title}</p>
        {subtitle ? <p className="mt-0.5 line-clamp-2 text-[10px] leading-[13px] text-slate-500">{subtitle}</p> : null}
        {timestamp ? <p className="mt-0.5 text-[10px] text-slate-500">{timestamp}</p> : null}
      </div>
    </div>
  );
}

function RelatedFileCard({ file }: { file: DetailRelatedFile }) {
  const tone = file.tone === "sheet" ? "green" : file.tone === "deck" ? "purple" : "blue";
  return (
    <div className="flex items-center justify-between gap-3 rounded-[18px] border border-slate-200 bg-white px-[14px] py-2 shadow-[0_4px_12px_rgba(15,23,42,0.03)]">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[11px] border border-slate-200 bg-white">
          <SmallIcon type={file.tone} tone={tone} />
        </div>
        <div>
          <p className="truncate text-[13px] font-semibold text-slate-900">{file.title}</p>
          <p className="mt-1 text-[12px] text-slate-500">{file.updatedAt}</p>
        </div>
      </div>
    </div>
  );
}

function ActivityRow({ item }: { item: DetailActivity }) {
  const tone = item.tone === "doc" ? "blue" : item.tone === "route" ? "purple" : item.tone === "data" ? "green" : "slate";
  const icon = item.tone === "doc" ? "doc" : item.tone === "route" ? "deck" : item.tone === "data" ? "sheet" : "session";
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[10px] bg-slate-50">
          <SmallIcon type={icon} tone={tone as "blue" | "green" | "purple" | "orange" | "slate" | "red"} />
        </div>
        <p className="truncate text-[12px] text-slate-700">{item.title}</p>
      </div>
      <span className="text-[12px] text-slate-400">{item.time}</span>
    </div>
  );
}

function normalizeArtifactKind(artifact?: SessionDetailData["artifact"]): "ppt" | "docx" | "board" | "unknown" {
  const kind = (artifact?.kind ?? "").toLowerCase();
  if (kind === "ppt" || kind === "docx" || kind === "board") return kind;
  return "unknown";
}

function normalizeArtifactState(status?: string | null) {
  const normalized = (status ?? "").toLowerCase();
  if (normalized === "done" || normalized === "completed" || normalized === "已同步") {
    return { label: "已完成", tone: "emerald", progress: 100 };
  }
  if (normalized === "failed" || normalized.includes("失败")) {
    return { label: "失败", tone: "rose", progress: 100 };
  }
  if (normalized === "queued") {
    return { label: "排队中", tone: "blue", progress: 8 };
  }
  if (normalized === "进行中" || normalized === "running" || normalized === "generating_slides" || normalized === "generating_notes" || normalized === "exporting" || normalized === "generating_design" || normalized === "parsing_file") {
    return { label: "进行中", tone: "blue", progress: 48 };
  }
  return { label: status || "待处理", tone: "slate", progress: 0 };
}

type AgentChatResponseWire = {
  session_id: string;
  intent: "chat" | "docx" | "ppt" | "board";
  status: "completed" | "failed";
  message: string;
  events?: Array<{
    event?: string | null;
    status?: string | null;
    message?: string | null;
    payload?: Record<string, unknown> | null;
  }> | null;
  artifact?: {
    kind?: string | null;
    content?: string | null;
    job_id?: string | null;
    download_url?: string | null;
    progress?: number | null;
    current_step?: string | null;
    task_id?: string | null;
    status?: string | null;
    whiteboard_id?: string | null;
    preview_url?: string | null;
    sharing_url?: string | null;
    result_summary?: string | null;
    error_message?: string | null;
  } | null;
  plan?: {
    goal?: string | null;
    intent?: string | null;
    task_complexity?: string | null;
    missing_info?: string[] | null;
    need_clarification?: boolean | null;
    questions?: string[] | null;
    assumptions?: string[] | null;
    clarification_needed?: boolean | null;
    clarification_question?: string | null;
    summary?: string | null;
    visible_summary?: string | null;
    final_output?: {
      format?: string | null;
      requirements?: string[] | null;
    } | null;
    steps?: Array<{
      id?: string | null;
      step_id?: string | null;
      title?: string | null;
      description?: string | null;
      type?: string | null;
      tool?: string | null;
      input?: Record<string, unknown> | null;
      expected_output?: string | null;
      depends_on?: string[] | null;
      status?: string | null;
    }>;
  } | null;
  error?: string | null;
};

type PPTPreviewSlide = {
  slide_number: number;
  title?: string | null;
  template?: string | null;
  right_items?: string[] | null;
};

type PPTPreview = {
  job_id: string;
  title?: string | null;
  subtitle?: string | null;
  page_count: number;
  status: string;
  progress: number;
  download_url?: string | null;
  slides: PPTPreviewSlide[];
};

type BoardImagePreview = {
  whiteboard_id: string;
  preview_url: string;
};

type DocumentAutoSyncWire = {
  session_id: string;
  status: "completed" | "failed" | string;
  message: string;
  document_url?: string | null;
};

type DocumentAutoSyncState = "idle" | "dirty" | "syncing" | "synced" | "failed";

function toDetailArtifact(artifact?: AgentChatResponseWire["artifact"]): DetailDocumentArtifact | undefined {
  if (!artifact) return undefined;
  return {
    kind: artifact.kind,
    content: artifact.content,
    jobId: artifact.job_id,
    downloadUrl: artifact.download_url,
    progress: artifact.progress,
    currentStep: artifact.current_step,
    status: artifact.status,
    whiteboardId: artifact.whiteboard_id,
    previewUrl: artifact.preview_url,
    sharingUrl: artifact.sharing_url,
    resultSummary: artifact.result_summary,
    errorMessage: artifact.error_message,
  };
}

function toPlanningSteps(plan?: AgentChatResponseWire["plan"]): PlanningStepWire[] {
  const steps = plan?.steps;
  if (!Array.isArray(steps)) return [];
  return steps.map((step, index) => ({
    id: step.id || step.step_id || String(index + 1),
    title: step.title || step.description || `步骤 ${index + 1}`,
    description: step.description || undefined,
    type: step.type || undefined,
    tool: step.tool || undefined,
    input: step.input || undefined,
    expectedOutput: step.expected_output || undefined,
    dependsOn: step.depends_on || [],
    status: step.status === "completed" || step.status === "running" || step.status === "warning" ? step.status : "pending",
  }));
}

function toPlanningPlan(plan?: AgentChatResponseWire["plan"]): PlanningPlanWire | null {
  const steps = toPlanningSteps(plan);
  const hasSummary = Boolean(plan?.visible_summary || plan?.summary || plan?.goal);
  const hasClarification = Boolean(plan?.clarification_question) || Boolean(plan?.questions?.length) || Boolean(plan?.missing_info?.length);
  const hasFinalOutput = Boolean(plan?.final_output?.format) || Boolean(plan?.final_output?.requirements?.length);
  if (!plan || (!steps.length && !hasSummary && !hasClarification && !hasFinalOutput)) return null;
  return {
    goal: plan.goal || "",
    intent: plan.intent || "",
    taskComplexity: plan.task_complexity || "medium",
    missingInfo: plan.missing_info || [],
    needClarification: Boolean(plan.need_clarification),
    questions: plan.questions || [],
    assumptions: plan.assumptions || [],
    clarificationNeeded: Boolean(plan.clarification_needed),
    clarificationQuestion: plan.clarification_question || null,
    summary: plan.visible_summary || plan.summary || "",
    steps,
    finalOutput: plan.final_output
      ? {
          format: plan.final_output.format || "",
          requirements: plan.final_output.requirements || [],
        }
      : undefined,
  };
}

function formatMessageTime(date = new Date()) {
  const hh = date.getHours().toString().padStart(2, "0");
  const mm = date.getMinutes().toString().padStart(2, "0");
  return `${hh}:${mm}`;
}

function agentToolCallText(intent: AgentChatResponseWire["intent"], artifact?: DetailDocumentArtifact) {
  const kind = artifact?.kind || intent;
  if (kind === "docx") return "好的，我现在调用文档生成能力，生成内容并同步到飞书。";
  if (kind === "ppt") return "好的，我现在调用 AI PPT 能力，创建生成任务并等待导出。";
  if (kind === "board") return "好的，我现在调用飞书画板能力，把任务落到画板流程里。";
  return "好的，我现在直接回复这个问题。";
}

function planningMessageBody(plan: PlanningPlanWire) {
  const clarificationLine =
    plan.questions?.[0] ||
    plan.clarificationQuestion ||
    (plan.missingInfo?.length ? `待补充信息：${plan.missingInfo.join("、")}` : "");
  const lines = ["任务理解与规划", plan.summary || plan.goal, clarificationLine].filter(Boolean);
  const steps = plan.steps
    .slice(0, 6)
    .map((step, index) => `${index + 1}. ${step.title}${step.description ? `：${step.description}` : ""}`);
  return [...lines, ...steps].join("\n");
}

function ragScoreLabel(score: number) {
  if (!Number.isFinite(score) || score <= 0) return "";
  return ` · ${(score * 100).toFixed(0)}%`;
}

function ragSnippet(content: string) {
  const normalized = content.replace(/\s+/g, " ").trim();
  if (!normalized) return "命中知识库资料，已注入本轮 Agent 上下文。";
  return normalized.length > 86 ? `${normalized.slice(0, 86)}...` : normalized;
}

function ragSourcesToContextSources(sources: RetrievedSourceWire[]): DetailSourceItem[] {
  return sources.map((source, index) => ({
    id: `rag:${source.sourceId}:${index}`,
    title: source.title || "RAG 命中资料",
    description: `RAG${ragScoreLabel(source.score)} · ${ragSnippet(source.content)}`,
    status: "completed",
  }));
}

function ragSourcesToEvidence(sources: RetrievedSourceWire[]): DetailEvidenceItem[] {
  return sources.map((source, index) => ({
    id: `rag:evidence:${source.sourceId}:${index}`,
    title: source.title || "RAG 命中资料",
    description: ragSnippet(source.content),
    tone: source.sourceType === "chat_history" ? "chat" : source.sourceType === "artifact" ? "record" : "document",
  }));
}

function mergeById<T extends { id: string }>(base: T[], extra: T[]) {
  const seen = new Set(base.map((item) => item.id));
  return [...base, ...extra.filter((item) => !seen.has(item.id))];
}

function wantsNewDocument(text: string) {
  const normalized = text.toLowerCase();
  return ["新建", "重新生成", "重新写", "重写一份", "另写", "另起", "再写一份", "再生成一份", "生成新", "新文档", "new document", "create new", "regenerate"].some(
    (keyword) => text.includes(keyword) || normalized.includes(keyword),
  );
}

function sectionsToMarkdown(sections: SessionDetailData["document"]["sections"]) {
  return sections
    .map((section) => {
      const body = section.body ? `\n\n${section.body}` : "";
      return `## ${section.title}${body}`;
    })
    .join("\n\n");
}

function ArtifactPresenter({
  artifact,
  sessionId,
  markdown,
  sections,
  streaming = false,
  editable = false,
  onMarkdownChange,
  autoSyncState = "idle",
  autoSyncError,
}: {
  artifact?: SessionDetailData["artifact"];
  sessionId: string;
  markdown?: string | null;
  sections: SessionDetailData["document"]["sections"];
  streaming?: boolean;
  editable?: boolean;
  onMarkdownChange?: (nextMarkdown: string) => void;
  autoSyncState?: DocumentAutoSyncState;
  autoSyncError?: string | null;
}) {
  const kind = normalizeArtifactKind(artifact);
  const state = normalizeArtifactState(artifact?.status);
  const title =
    kind === "ppt" ? artifact?.title || "AI PPT" : kind === "board" ? artifact?.title || "飞书画板" : artifact?.title || "文档产物";
  const [pptPreview, setPptPreview] = useState<PPTPreview | null>(null);
  const [selectedSlideNumber, setSelectedSlideNumber] = useState(1);
  const [brokenSlidesByPreview, setBrokenSlidesByPreview] = useState<Record<string, Set<number>>>({});
  const boardViewportRef = useRef<HTMLDivElement | null>(null);
  const boardDragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    scrollLeft: number;
    scrollTop: number;
  } | null>(null);
  const [boardPreview, setBoardPreview] = useState<{
    whiteboardId: string;
    previewUrl: string | null;
    state: "ready" | "failed";
  } | null>(null);
  const [boardZoom, setBoardZoom] = useState(1.7);
  const [isDocEditing, setIsDocEditing] = useState(false);
  const matchedBoardPreview =
    boardPreview && boardPreview.whiteboardId === artifact?.whiteboardId ? boardPreview : null;
  const effectiveBoardPreviewUrl =
    artifact?.previewUrl ?? matchedBoardPreview?.previewUrl ?? null;
  const effectiveBoardPreviewState =
    artifact?.previewUrl ? "ready" : matchedBoardPreview?.state ?? "loading";
  const previewSlides =
    pptPreview?.slides?.length
      ? pptPreview.slides
      : [1, 2, 3].map((slide) => ({ slide_number: slide, title: slide === 1 ? "封面" : slide === 2 ? "内容" : "结尾", template: "" }));
  const selectedSlide =
    previewSlides.find((slide) => slide.slide_number === selectedSlideNumber) ?? previewSlides[0];
  const pptPreviewKey = useMemo(() => {
    if (!artifact?.jobId) return "ppt:placeholder";
    const slideCount = pptPreview?.slides?.length ?? 0;
    const statusKey = pptPreview?.status ?? artifact?.status ?? "unknown";
    return `${artifact.jobId}:${statusKey}:${slideCount}`;
  }, [artifact?.jobId, artifact?.status, pptPreview?.slides?.length, pptPreview?.status]);
  const brokenSlides = brokenSlidesByPreview[pptPreviewKey] ?? new Set<number>();
  const boardZoomPct = Math.round(boardZoom * 100);
  const docMarkdown = markdown || sections.map((section) => `## ${section.title}\n\n${section.body ?? ""}`).join("\n\n");
  const docFileName = `${(title || "Eko 文档").replace(/[\\/:*?"<>|]/g, "_")}.doc`;
  const docSharingUrl = artifact?.sharingUrl ?? "";
  const artifactSharingUrl = artifact?.sharingUrl ?? "";
  const docEditorHeight = Math.min(2400, Math.max(560, docMarkdown.split(/\r?\n/).length * 28 + 120));
  const canEditDocument = kind === "docx" && editable && !streaming;
  const isDocEditorOpen = canEditDocument && isDocEditing;
  const autoSyncLabel =
    autoSyncState === "dirty"
      ? "待自动同步"
      : autoSyncState === "syncing"
        ? "自动同步中"
        : autoSyncState === "synced"
          ? "已自动同步"
          : autoSyncState === "failed"
            ? "同步失败"
            : "";
  const autoSyncClass =
    autoSyncState === "failed"
      ? "border-rose-200 bg-rose-50 text-rose-600"
      : autoSyncState === "synced"
        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
        : autoSyncState === "syncing"
          ? "border-blue-200 bg-blue-50 text-blue-700"
          : "border-slate-200 bg-slate-50 text-slate-500";

  const handleCopyDocLink = useCallback(async () => {
    if (!docSharingUrl || typeof navigator === "undefined" || !navigator.clipboard) return;
    await navigator.clipboard.writeText(docSharingUrl);
  }, [docSharingUrl]);

  const handleCopyArtifactLink = useCallback(async () => {
    if (!artifactSharingUrl || typeof navigator === "undefined" || !navigator.clipboard) return;
    await navigator.clipboard.writeText(artifactSharingUrl);
  }, [artifactSharingUrl]);

  const handleSaveDoc = useCallback(() => {
    if (typeof window === "undefined" || !docMarkdown.trim()) return;
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title></head><body><pre style="font-family:Arial,'Microsoft YaHei',sans-serif;white-space:pre-wrap;line-height:1.7;">${docMarkdown
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")}</pre></body></html>`;
    const blob = new Blob([html], { type: "application/msword;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = docFileName;
    a.click();
    URL.revokeObjectURL(url);
  }, [docFileName, docMarkdown, title]);

  const handleBoardPointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!effectiveBoardPreviewUrl || event.button !== 0) return;
    const target = event.currentTarget;
    boardDragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      scrollLeft: target.scrollLeft,
      scrollTop: target.scrollTop,
    };
    target.setPointerCapture(event.pointerId);
    target.dataset.dragging = "true";
  }, [effectiveBoardPreviewUrl]);

  const handleBoardPointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const drag = boardDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    const target = event.currentTarget;
    target.scrollLeft = drag.scrollLeft - (event.clientX - drag.startX);
    target.scrollTop = drag.scrollTop - (event.clientY - drag.startY);
  }, []);

  const endBoardDrag = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const drag = boardDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    boardDragRef.current = null;
    event.currentTarget.dataset.dragging = "false";
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }, []);

  const jobId = artifact?.jobId;
  useEffect(() => {
    if (kind !== "ppt" || !jobId) return;
    let cancelled = false;
    const fetchPreview = () =>
      fetchEkoJson<PPTPreview>(`/api/v1/ppt/preview/${encodeURIComponent(jobId)}`)
        .then((preview) => {
          if (!cancelled) setPptPreview(preview);
        })
        .catch(() => {
          if (!cancelled) setPptPreview(null);
        });
    fetchPreview();
    const interval = setInterval(fetchPreview, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [jobId, kind, artifact?.status]);

  useEffect(() => {
    if (kind !== "board") return;
    if (artifact?.previewUrl) {
      return;
    }
    if (!artifact?.whiteboardId) {
      return;
    }

    let cancelled = false;
    const whiteboardId = artifact.whiteboardId;
    fetchEkoJson<BoardImagePreview>(`/api/v1/feishu/board/image/${encodeURIComponent(artifact.whiteboardId)}`)
      .then((preview) => {
        if (cancelled) return;
        setBoardPreview({ whiteboardId, previewUrl: preview.preview_url, state: "ready" });
      })
      .catch(() => {
        if (cancelled) return;
        setBoardPreview({ whiteboardId, previewUrl: null, state: "failed" });
      });
    return () => {
      cancelled = true;
    };
  }, [artifact?.previewUrl, artifact?.whiteboardId, kind]);

  if (!artifact && !markdown && sections.length === 0) return null;

  return (
    <div className="relative flex h-full min-h-[520px] w-full flex-col bg-white">
      {kind === "ppt" ? (
        <div className="flex min-h-0 flex-1 items-center justify-center px-4 py-4">
          <div className="flex w-full max-w-[1120px] flex-col gap-3">
            <div className="aspect-[16/9] w-full overflow-hidden rounded-[16px] border border-slate-200 bg-white shadow-[0_18px_44px_rgba(15,23,42,0.06)]">
              {selectedSlide && artifact?.jobId && !brokenSlides.has(selectedSlide.slide_number) ? (
                <Image
                  src={apiUrl(`/api/v1/ppt/preview/${encodeURIComponent(artifact.jobId)}/slides/${selectedSlide.slide_number}`)}
                  alt={selectedSlide.title || title}
                  width={1600}
                  height={900}
                  unoptimized
                  sizes="(max-width: 1120px) 100vw, 1120px"
                  className="h-full w-full object-cover"
                  onError={() =>
                    setBrokenSlidesByPreview((prev) => {
                      const next = { ...prev };
                      const nextSet = new Set(next[pptPreviewKey] ?? []);
                      nextSet.add(selectedSlide.slide_number);
                      next[pptPreviewKey] = nextSet;
                      return next;
                    })
                  }
                />
              ) : selectedSlide && brokenSlides.has(selectedSlide.slide_number) ? (
                <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-50 to-white p-8">
                  <div className="text-center">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100">
                      <svg className="h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-slate-800">{selectedSlide.title || title}</h3>
                    <p className="mt-1 text-sm text-slate-400">第 {selectedSlide.slide_number} 页</p>
                  </div>
                </div>
              ) : (
                <div className="flex h-full flex-col p-6">
                  <div className="flex min-w-0 items-center justify-between gap-3">
                    <h3 className="truncate text-[18px] font-semibold text-slate-950">{title}</h3>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-[12px] font-semibold text-emerald-700">{state.label}</span>
                  </div>
                  <div className="mt-8 animate-pulse space-y-4">
                    <div className="h-4 w-7/12 rounded-full bg-slate-200" />
                    <div className="h-3 w-10/12 rounded-full bg-slate-100" />
                    <div className="h-3 w-8/12 rounded-full bg-slate-100" />
                    <div className="h-56 rounded-[16px] bg-slate-100" />
                  </div>
                </div>
              )}
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {artifact?.errorMessage ? <span className="rounded-full bg-rose-50 px-3 py-2 text-[12px] font-semibold text-rose-700">{artifact.errorMessage}</span> : null}
              {artifactSharingUrl ? (
                <>
                  <button type="button" onClick={handleCopyArtifactLink} className="inline-flex h-9 items-center justify-center rounded-[12px] border border-slate-200 bg-white px-3 text-[13px] font-semibold text-slate-600 shadow-[0_8px_18px_rgba(15,23,42,0.06)] hover:border-blue-200 hover:text-blue-600">
                    复制链接
                  </button>
                  <a href={artifactSharingUrl} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center justify-center rounded-[12px] bg-slate-900 px-3 text-[13px] font-semibold text-white shadow-[0_10px_20px_rgba(15,23,42,0.14)] hover:bg-blue-600">
                    打开飞书
                  </a>
                </>
              ) : null}
              {artifact?.downloadUrl ? (
                <a href={artifact.downloadUrl} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center justify-center rounded-[12px] bg-blue-600 px-3 text-[13px] font-semibold text-white shadow-[0_10px_20px_rgba(37,99,235,0.18)]">
                  下载 PPT
                </a>
              ) : null}
            </div>
            <div className="flex min-w-0 gap-2 overflow-x-auto pb-1">
              {previewSlides.slice(0, 8).map((slide) => (
                <button
                  key={slide.slide_number}
                  type="button"
                  onClick={() => {
                    setSelectedSlideNumber(slide.slide_number);
                    setBrokenSlidesByPreview((prev) => {
                      const current = prev[pptPreviewKey];
                      if (!current?.has(slide.slide_number)) return prev;
                      const next = { ...prev };
                      const nextSet = new Set(current);
                      nextSet.delete(slide.slide_number);
                      next[pptPreviewKey] = nextSet;
                      return next;
                    });
                  }}
                  className={[
                    "w-[132px] shrink-0 overflow-hidden rounded-[12px] border bg-white text-left shadow-[0_8px_20px_rgba(15,23,42,0.04)] transition",
                    selectedSlide?.slide_number === slide.slide_number ? "border-blue-500 ring-2 ring-blue-100" : "border-slate-200 hover:border-blue-300",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between px-2 py-1.5 text-[10px] font-semibold text-slate-400">
                    <span>Slide {slide.slide_number}</span>
                    <span className="truncate">{slide.title || slide.template || ""}</span>
                  </div>
                  {pptPreview && artifact?.jobId && !brokenSlides.has(slide.slide_number) ? (
                    <Image
                      src={apiUrl(`/api/v1/ppt/preview/${encodeURIComponent(artifact.jobId)}/slides/${slide.slide_number}`)}
                      alt={slide.title || `Slide ${slide.slide_number}`}
                      width={264}
                      height={149}
                      unoptimized
                      sizes="132px"
                      className="aspect-[16/9] w-full object-cover"
                      onError={() =>
                        setBrokenSlidesByPreview((prev) => {
                          const next = { ...prev };
                          const nextSet = new Set(next[pptPreviewKey] ?? []);
                          nextSet.add(slide.slide_number);
                          next[pptPreviewKey] = nextSet;
                          return next;
                        })
                      }
                    />
                  ) : (
                    <div className="mx-2 mb-2 flex aspect-[16/9] items-center justify-center rounded-[10px] bg-slate-100 text-[11px] font-medium text-slate-400">
                      {slide.slide_number}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : kind === "board" ? (
        <div className="flex min-h-0 flex-1 flex-col px-5 py-5">
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-[0_18px_44px_rgba(15,23,42,0.06)]">
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-[16px] font-semibold text-slate-950">{title}</p>
                <p className="mt-0.5 truncate text-[12px] text-slate-500">
                  {artifact?.whiteboardId ? `Whiteboard ${artifact.whiteboardId}` : "飞书画板预览"}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {effectiveBoardPreviewUrl ? (
                  <div className="flex h-9 items-center rounded-[12px] border border-slate-200 bg-white p-1 shadow-[0_6px_16px_rgba(15,23,42,0.04)]">
                    <button
                      type="button"
                      onClick={() => setBoardZoom((zoom) => Math.max(0.7, Number((zoom - 0.15).toFixed(2))))}
                      className="flex h-7 w-7 items-center justify-center rounded-[8px] text-[16px] font-semibold text-slate-600 hover:bg-slate-50"
                      aria-label="缩小画板预览"
                    >
                      -
                    </button>
                    <span className="w-[54px] text-center text-[12px] font-semibold text-slate-600">{boardZoomPct}%</span>
                    <button
                      type="button"
                      onClick={() => setBoardZoom((zoom) => Math.min(3, Number((zoom + 0.15).toFixed(2))))}
                      className="flex h-7 w-7 items-center justify-center rounded-[8px] text-[16px] font-semibold text-slate-600 hover:bg-slate-50"
                      aria-label="放大画板预览"
                    >
                      +
                    </button>
                    <button
                      type="button"
                      onClick={() => setBoardZoom(1)}
                      className="ml-1 h-7 rounded-[8px] px-2 text-[12px] font-semibold text-slate-500 hover:bg-slate-50"
                    >
                      100%
                    </button>
                    <button
                      type="button"
                      onClick={() => setBoardZoom(1.7)}
                      className="h-7 rounded-[8px] px-2 text-[12px] font-semibold text-blue-600 hover:bg-blue-50"
                    >
                      放大
                    </button>
                  </div>
                ) : null}
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-[12px] font-semibold text-emerald-700">
                  {state.label}
                </span>
              </div>
            </div>
            <div className="min-h-0 flex-1 bg-slate-50/70 p-3">
              {effectiveBoardPreviewUrl ? (
                <div
                  ref={boardViewportRef}
                  onPointerDown={handleBoardPointerDown}
                  onPointerMove={handleBoardPointerMove}
                  onPointerUp={endBoardDrag}
                  onPointerCancel={endBoardDrag}
                  onPointerLeave={endBoardDrag}
                  className="h-full min-h-[420px] min-w-0 flex-1 cursor-grab touch-none select-none overflow-auto rounded-[14px] bg-white active:cursor-grabbing data-[dragging=true]:cursor-grabbing"
                >
                  <div className="flex min-h-full min-w-full items-start justify-center p-4">
                    <Image
                      src={effectiveBoardPreviewUrl}
                      alt={title}
                      width={1920}
                      height={1080}
                      unoptimized
                      sizes="100vw"
                      draggable={false}
                      style={{ width: `${boardZoom * 100}%`, minWidth: `${Math.round(580 * boardZoom)}px`, height: "auto" }}
                      className="pointer-events-none max-w-none object-contain"
                    />
                  </div>
                </div>
              ) : (
                <div className="flex h-full min-h-[420px] min-w-0 flex-1 flex-col items-center justify-center rounded-[14px] border border-dashed border-slate-200 bg-white px-6 text-center">
                  <p className="text-[15px] font-semibold text-slate-900">
                    {effectiveBoardPreviewState === "loading" ? "正在加载画板预览" : "暂时无法显示画板预览"}
                  </p>
                  <p className="mt-2 max-w-[520px] text-[13px] leading-6 text-slate-500">
                    {effectiveBoardPreviewState === "failed"
                      ? "飞书图片导出接口没有返回预览图，仍可打开飞书画板继续查看和编辑。"
                      : artifact?.resultSummary || "画板资源已准备，可打开真实画板继续编辑。"}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto px-8 py-5">
          <div className="sticky top-0 z-10 mx-auto mb-5 flex max-w-[720px] items-center justify-between gap-3 border-b border-slate-100 bg-white/95 pb-3 backdrop-blur">
            <div className="min-w-0">
              <p className="truncate text-[13px] font-semibold text-slate-900">{title}</p>
              <p className="mt-0.5 text-[11px] text-slate-400">
                {streaming ? "正在生成" : canEditDocument ? (isDocEditorOpen ? "Markdown 源码编辑，自动同步" : "文档预览") : state.label}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {kind === "docx" && autoSyncLabel ? (
                <span className={`inline-flex h-8 items-center justify-center rounded-[10px] border px-2.5 text-[12px] font-semibold ${autoSyncClass}`} title={autoSyncError || autoSyncLabel}>
                  {autoSyncLabel}
                </span>
              ) : null}
              {kind === "docx" && docSharingUrl ? (
                <>
                  <button type="button" onClick={handleCopyDocLink} className="inline-flex h-8 items-center justify-center rounded-[10px] border border-slate-200 bg-white px-2.5 text-[12px] font-semibold text-slate-600 hover:border-blue-200 hover:text-blue-600">
                    复制链接
                  </button>
                  <a href={docSharingUrl} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center justify-center rounded-[10px] bg-slate-900 px-2.5 text-[12px] font-semibold text-white hover:bg-blue-600">
                    打开飞书
                  </a>
                </>
              ) : null}
              {kind === "docx" ? (
                <button type="button" onClick={handleSaveDoc} className="inline-flex h-8 items-center justify-center rounded-[10px] border border-slate-200 bg-white px-2.5 text-[12px] font-semibold text-slate-600 hover:border-blue-200 hover:text-blue-600">
                  下载文档
                </button>
              ) : null}
              {canEditDocument ? (
                <button
                  type="button"
                  onClick={() => setIsDocEditing((editing) => !editing)}
                  className={[
                    "inline-flex h-8 items-center justify-center rounded-[10px] px-2.5 text-[12px] font-semibold transition",
                    isDocEditorOpen
                      ? "border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
                      : "border border-slate-200 bg-white text-slate-600 hover:border-blue-200 hover:text-blue-600",
                  ].join(" ")}
                >
                  {isDocEditorOpen ? "预览" : "编辑"}
                </button>
              ) : null}
            </div>
          </div>
          {streaming ? (
            <div className="mx-auto max-w-[720px] whitespace-pre-wrap break-words text-[14px] leading-7 text-slate-700">
              {markdown}
              <span className="ml-1 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse rounded-full bg-blue-500" aria-label="写入中" />
            </div>
          ) : (
            isDocEditorOpen ? (
              <textarea
                value={docMarkdown}
                onChange={(event) => onMarkdownChange?.(event.target.value)}
                aria-label="编辑 Markdown 文档源码"
                spellCheck={false}
                style={{ minHeight: docEditorHeight }}
                className="mx-auto block w-full max-w-[720px] resize-y rounded-[14px] border border-blue-100 bg-blue-50/20 px-4 py-3 font-mono text-[13px] leading-7 text-slate-800 outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-50"
              />
            ) : (
              <div className="prose prose-sm mx-auto max-w-[720px] text-slate-700 prose-headings:my-3 prose-p:my-2 prose-ul:my-2 prose-li:my-0.5">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {docMarkdown}
                </ReactMarkdown>
              </div>
            )
          )}
        </div>
      )}

      <div className="absolute bottom-5 right-5 flex items-center gap-2">
        {artifact?.errorMessage && kind !== "ppt" ? <span className="rounded-full bg-rose-50 px-3 py-2 text-[12px] font-semibold text-rose-700">{artifact.errorMessage}</span> : null}
        {kind === "board" ? (
          <Link href={artifact?.sharingUrl || `/canvas?session=${encodeURIComponent(sessionId)}`} prefetch={false} className="inline-flex h-9 items-center justify-center rounded-[12px] bg-blue-600 px-3 text-[13px] font-semibold text-white shadow-[0_10px_20px_rgba(37,99,235,0.18)]">
            打开画布
          </Link>
        ) : null}
      </div>
    </div>
  );
}

function SectionCard({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="min-w-0 rounded-[22px] border border-slate-200/90 bg-white px-4 py-3.5 shadow-[0_12px_24px_rgba(148,163,184,0.06)]">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <h3 className="truncate text-[15px] font-semibold text-slate-950">{title}</h3>
        <div className="shrink-0">{action}</div>
      </div>
      <div className="mt-3.5 min-w-0">{children}</div>
    </section>
  );
}

function CanvasNodeCard({
  title,
  index,
  bullets,
  icon,
  status = "default",
}: {
  title: string;
  index: number;
  bullets: string[];
  icon: "trend" | "rocket" | "calendar" | "spark" | "alert" | "check";
  status?: "default" | "draft";
}) {
  const toneMap = {
    trend: "purple",
    rocket: "blue",
    calendar: "green",
    spark: "orange",
    alert: "red",
    check: "purple",
  } as const;

  const ringMap = {
    trend: "border-violet-200 bg-violet-50 text-violet-600",
    rocket: "border-blue-200 bg-blue-50 text-blue-600",
    calendar: "border-emerald-200 bg-emerald-50 text-emerald-600",
    spark: "border-amber-200 bg-amber-50 text-amber-600",
    alert: "border-rose-200 bg-rose-50 text-rose-500",
    check: "border-violet-200 bg-violet-50 text-violet-600",
  } as const;

  const cardBorderMap = {
    trend: "border-violet-200",
    rocket: "border-blue-200",
    calendar: "border-emerald-200",
    spark: "border-amber-200",
    alert: "border-rose-200",
    check: "border-violet-200",
  } as const;

  return (
    <div
      className={[
        "relative flex min-h-[92px] min-w-0 flex-col overflow-hidden rounded-[15px] border bg-white px-2 py-2 shadow-[0_8px_18px_rgba(15,23,42,0.05)]",
        status === "draft" ? "border-dashed border-violet-300 bg-violet-50/60" : cardBorderMap[icon],
      ].join(" ")}
    >
      {status === "draft" ? (
        <div className="absolute -top-2 left-4 inline-flex rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-600">
          待补充
        </div>
      ) : null}
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="flex min-w-0 flex-1 items-start gap-2">
          <span className={`mt-0.5 flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold ${ringMap[icon]}`}>{index}</span>
          <h4 className="min-w-0 break-words text-[12px] font-semibold leading-snug text-slate-950 line-clamp-2">{title}</h4>
        </div>
        <div className="mt-0.5 shrink-0">
          <SmallIcon type={icon} tone={toneMap[icon]} />
        </div>
      </div>
      <ul className="mt-1.5 min-h-0 flex-1 space-y-0.5 overflow-hidden text-[10px] leading-snug text-slate-600">
        {bullets.map((bullet, bulletIndex) => (
          <li key={`${index}-${bulletIndex}-${bullet.slice(0, 48)}`} className="break-words line-clamp-2">
            • {bullet}
          </li>
        ))}
      </ul>
    </div>
  );
}

function StepperStatusLegend() {
  return (
    <div
      role="presentation"
      className="flex shrink-0 flex-wrap items-center justify-end gap-x-2 gap-y-1 text-[9px] leading-tight text-slate-500"
    >
      <span className="inline-flex items-center gap-1">
        <span className="h-1 w-1 shrink-0 rounded-full bg-emerald-500" aria-hidden />
        已完成
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-1 w-1 shrink-0 rounded-full bg-blue-500" aria-hidden />
        进行中
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-1 w-1 shrink-0 rounded-full bg-slate-300" aria-hidden />
        待处理
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-1 w-1 shrink-0 rounded-full bg-amber-400" aria-hidden />
        预警
      </span>
    </div>
  );
}

function canonicalWorkflowSteps(kind: "ppt" | "docx" | "board" | "unknown"): WorkflowStep[] {
  const generateTitle =
    kind === "ppt" ? "生成 AI PPT" : kind === "board" ? "生成飞书画板" : kind === "docx" ? "生成文稿" : "生成回复 / 文稿";
  const syncTitle = kind === "board" ? "同步飞书画板" : kind === "ppt" ? "导出 PPT 文件" : kind === "docx" ? "同步飞书文档" : "同步结果";
  return [
    { id: "1", title: "分析 IM 上下文", status: "pending" },
    { id: "2", title: "判断当前意图", status: "pending" },
    { id: "3", title: "按需检索 RAG", status: "pending" },
    { id: "4", title: generateTitle, status: "pending" },
    { id: "5", title: syncTitle, status: "pending" },
    { id: "6", title: "回传飞书群", status: "pending" },
  ];
}

function mergeWorkflowSteps(
  base: WorkflowStep[],
  live: PlanningStepWire[],
  kind: "ppt" | "docx" | "board" | "unknown",
  phase: string,
  artifactStatus?: string | null,
): WorkflowStep[] {
  const canonical = canonicalWorkflowSteps(kind);
  const source = live.length ? live : canonical;
  const byPosition = new Map((live.length ? live : base).map((step, index) => [String(index + 1), step.status]));
  const normalizedStatus = (artifactStatus ?? "").toLowerCase();
  const terminalDone = normalizedStatus === "done" || normalizedStatus === "completed" || normalizedStatus === "已同步";
  const terminalFailed = normalizedStatus === "failed" || phase === "ERROR";

  const withSourceStatus = source.map((step, index) => ({
    ...step,
    id: String(index + 1),
    status: byPosition.get(String(index + 1)) ?? step.status,
  }));

  if (terminalDone) {
    return withSourceStatus.map((step) => ({ ...step, status: "completed" }));
  }

  if (terminalFailed) {
    return withSourceStatus.map((step, index) => ({
      ...step,
      status: index < 3 ? "completed" : index === 3 ? "warning" : step.status,
    }));
  }

  const activeIndex = live.length
    ? phase === "ANALYZING" || phase === "RETRIEVING"
      ? 0
      : phase === "GENERATING"
        ? Math.min(1, withSourceStatus.length - 1)
        : phase === "SYNCING"
          ? withSourceStatus.length - 1
          : -1
    : phase === "ANALYZING"
      ? 0
      : phase === "RETRIEVING"
        ? 2
        : phase === "GENERATING"
          ? 3
          : phase === "SYNCING"
            ? 4
            : -1;
  if (activeIndex >= 0) {
    return withSourceStatus.map((step, index) => ({
      ...step,
      status: index < activeIndex ? "completed" : index === activeIndex ? "running" : "pending",
    }));
  }

  return withSourceStatus;
}

function AgentRealtimeRibbon({
  phase,
  wsStatus,
  useMockFallback,
}: {
  phase: string;
  wsStatus: string;
  useMockFallback: boolean;
}) {
  const busy = phase === "ANALYZING" || phase === "RETRIEVING" || phase === "GENERATING" || phase === "SYNCING";
  return (
    <motion.div
      initial={false}
      animate={{ opacity: busy ? 1 : 0.72 }}
      className="flex shrink-0 flex-wrap items-center gap-1.5 text-[9px] text-slate-600"
    >
      <span className="rounded-full bg-slate-900 px-2 py-0.5 font-semibold tracking-tight text-white">{phase}</span>
      <span className="text-slate-500">
        实时链路 {wsStatus}
      </span>
      {useMockFallback ? (
        <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 font-semibold text-amber-700">
          DEMO 协议 mock，非真实后端推送
        </span>
      ) : null}
      {busy ? (
        <motion.span
          className="inline-flex h-2 w-2 rounded-full bg-blue-500"
          animate={{ scale: [1, 1.35, 1], opacity: [1, 0.55, 1] }}
          transition={{ repeat: Infinity, duration: 1.15, ease: "easeInOut" }}
        />
      ) : null}
    </motion.div>
  );
}

export function DocSessionWorkspace({ data }: { data: SessionDetailData }) {
  const { query: workspaceSearchQuery } = useSessionWorkspaceSearch();
  const setRuntimeSessionPatch = useAppStore((state) => state.setRuntimeSessionPatch);
  const conversationOpen = useAppStore((s) => s.sessionDetailChatOpen);
  const agentSlice = useAgentRuntimeStore((s) => s.sessions[data.id]);
  const [activeTab, setActiveTab] = useState<DetailTabKey>(data.defaultTab);
  const [messages, setMessages] = useState(data.messages);
  const selfAuthor = useMemo(() => {
    const counts = new Map<string, number>();
    for (const msg of messages) {
      if (msg.role === "member" && msg.author && msg.author !== "我" && msg.author !== "Eko" && msg.author !== "成员") {
        counts.set(msg.author, (counts.get(msg.author) || 0) + 1);
      }
    }
    let best = "";
    let bestCount = 0;
    for (const [author, count] of counts) {
      if (count > bestCount) {
        best = author;
        bestCount = count;
      }
    }
    return best || undefined;
  }, [messages]);
  const [localArtifact, setLocalArtifact] = useState<DetailDocumentArtifact | undefined>(data.artifact);
  const [manualDocumentMarkdown, setManualDocumentMarkdown] = useState<string | null>(null);
  const [docAutoSyncState, setDocAutoSyncState] = useState<DocumentAutoSyncState>("idle");
  const [docAutoSyncError, setDocAutoSyncError] = useState<string | null>(null);
  const docAutoSyncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const docAutoSyncAbortRef = useRef<AbortController | null>(null);
  const docAutoSyncSeqRef = useRef(0);
  const [sending, setSending] = useState(false);
  const [plannerEnabled, setPlannerEnabled] = useState(true);
  const isCanvasMode = data.layoutVariant === "canvas";
  const [canvasNodes, setCanvasNodes] = useState<DetailCanvasNode[]>(() => (isCanvasMode ? data.canvas.nodes : []));
  const [canvasActivities, setCanvasActivities] = useState<DetailActivity[]>(() =>
    isCanvasMode
      ? [
          { id: "canvas-generated", title: "画布已生成", time: "2 分钟前", tone: "route" },
          { id: "canvas-mode", title: "路由为画布模式", time: "3 分钟前", tone: "route" },
          { id: "canvas-data", title: "数据源连接成功", time: "3 分钟前", tone: "data" },
          { id: "canvas-session", title: "会话已开始", time: "4 分钟前", tone: "session" },
        ]
      : []
  );
  const [bitableStatus, setBitableStatus] = useState<WorkflowStatus>(isCanvasMode ? "warning" : "pending");
  const [archiveStatus, setArchiveStatus] = useState(isCanvasMode ? "草稿待确认" : "待同步");
  const [permissionStatus, setPermissionStatus] = useState(isCanvasMode ? "可同步" : "已验证");
  const [canvasNotice, setCanvasNotice] = useState<string | null>(null);
  const contextMessages = data.contextMessages ?? [];
  const shouldShowContextSelector = contextMessages.length > 0 && data.intent !== "chat";
  const hasActiveRealtimeConversationRef = useRef(false);

  hasActiveRealtimeConversationRef.current =
    agentSlice?.phase === "ANALYZING" ||
    agentSlice?.phase === "RETRIEVING" ||
    agentSlice?.phase === "GENERATING" ||
    agentSlice?.phase === "SYNCING";

  useEffect(() => {
    setMessages((current) => {
      if (hasActiveRealtimeConversationRef.current && data.messages.length < current.length) return current;
      return data.messages;
    });
  }, [data.messages]);
  const [contextExpanded, setContextExpanded] = useState(shouldShowContextSelector);
  const [contextStart, setContextStart] = useState(0);
  const [contextEnd, setContextEnd] = useState(Math.max(0, contextMessages.length - 1));
  const [contextSubmitting, setContextSubmitting] = useState(false);
  const [contextNotice, setContextNotice] = useState<string | null>(null);
  const [conversationFilter, setConversationFilter] = useState<"all" | "eko">("all");
  const [memoryExpanded, setMemoryExpanded] = useState(false);
  const canvasSyncActions = useMemo<DetailSyncAction[]>(
    () =>
      isCanvasMode
        ? [
            {
              id: "ca1",
              title: "同步到 Bitable",
              status: bitableStatus === "completed" ? "completed" : bitableStatus,
            },
            {
              id: "ca2",
              title: "发送到飞书群",
              status: archiveStatus === "已归档" ? "running" : "pending",
            },
            {
              id: "ca3",
              title: "生成待办",
              status: canvasNodes.length > 6 ? "running" : "pending",
            },
          ]
        : data.syncActions,
    [archiveStatus, bitableStatus, canvasNodes.length, data.syncActions, isCanvasMode]
  );
  const conversationTone = isCanvasMode ? "canvas" : "doc";
  const searchNeedle = workspaceSearchQuery.trim().toLowerCase();
  const filteredMessages = useMemo(() => {
    return messages.filter((m) => {
      if (conversationFilter === "eko" && m.role !== "eko" && m.author !== "Eko") return false;
      if (!searchNeedle) return true;
      const blob = [m.author, m.body, m.time, m.helperText].filter(Boolean).join(" ").toLowerCase();
      return blob.includes(searchNeedle);
    });
  }, [conversationFilter, messages, searchNeedle]);
  const runtimeContextSources = useMemo(
    () => mergeById(data.contextSources, ragSourcesToContextSources(agentSlice?.retrievedSources ?? [])),
    [agentSlice?.retrievedSources, data.contextSources],
  );
  const runtimeSourceEvidence = useMemo(
    () => mergeById(data.sourceEvidence, ragSourcesToEvidence(agentSlice?.retrievedSources ?? [])),
    [agentSlice?.retrievedSources, data.sourceEvidence],
  );
  const filteredContextSources = useMemo(() => {
    if (!searchNeedle) return runtimeContextSources;
    return runtimeContextSources.filter((item) => {
      const blob = [item.title, item.description].join(" ").toLowerCase();
      return blob.includes(searchNeedle);
    });
  }, [runtimeContextSources, searchNeedle]);
  const topRowNodes = canvasNodes.slice(0, 3);
  const bottomRowNodes = canvasNodes.slice(3, 6);

  useEffect(() => {
    if (!canvasNotice) return;
    const timer = window.setTimeout(() => setCanvasNotice(null), 2400);
    return () => window.clearTimeout(timer);
  }, [canvasNotice]);

  const handleRealtimeEnvelope = useCallback((raw: unknown) => {
    if (!raw || typeof raw !== "object") return;
    const body = raw as Record<string, unknown>;
    if (body.type === "TASK_COMPLETED") {
      const payload = (body.payload ?? {}) as Record<string, unknown>;
      const artifact = payload.artifact && typeof payload.artifact === "object" ? toDetailArtifact(payload.artifact as AgentChatResponseWire["artifact"]) : undefined;
      if (artifact?.kind === "docx" && (manualDocumentMarkdown === null || docAutoSyncState === "idle" || docAutoSyncState === "synced")) {
        const payloadStatus = typeof payload.status === "string" ? payload.status : null;
        const normalizedArtifact = {
          ...artifact,
          status: artifact.status ?? (payloadStatus === "completed" || payloadStatus === "done" || payloadStatus === "已同步" ? "completed" : payloadStatus),
        };
        setLocalArtifact(normalizedArtifact);
        setManualDocumentMarkdown(null);
        if (normalizedArtifact.status === "completed" || normalizedArtifact.status === "done" || normalizedArtifact.status === "已同步") {
          setDocAutoSyncState("synced");
        }
        setDocAutoSyncError(null);
      }
      return;
    }
    if (body.type !== "AGENT_MESSAGE") return;
    const payload = (body.payload ?? {}) as Record<string, unknown>;
    const content = typeof payload.content === "string" ? payload.content : "";
    if (!content.trim()) return;
    const role = typeof payload.role === "string" ? payload.role : "assistant";
    const isEko = role === "assistant" || role === "eko" || role === "bot" || role === "system";
    const replaceLast = payload.replace_last === true;
    const time = formatMessageTime();
    setMessages((prev) => {
      const nextMessage: SessionDetailData["messages"][number] = {
        id: `ws-${Date.now()}`,
        author: isEko ? "Eko" : "成员",
        role: isEko ? "eko" : "member",
        time,
        body: content,
        avatar: isEko ? "E" : "成",
        sent: true,
      };
      if (isEko) {
        const duplicateReplay = prev.some((message) => {
          if (message.role !== "eko") return false;
          const existing = message.body.trim();
          const incoming = content.trim();
          return existing === incoming || existing.includes(incoming);
        });
        if (duplicateReplay) return prev;
      }
      if (replaceLast && prev.length > 0 && prev[prev.length - 1].role === nextMessage.role) {
        const existing = prev[prev.length - 1].body.trim();
        const incoming = content.trim();
        if (existing.includes(incoming)) return prev;
        if (incoming.includes(existing)) {
          return [...prev.slice(0, -1), { ...nextMessage, id: prev[prev.length - 1].id }];
        }
        return [...prev.slice(0, -1), { ...nextMessage, id: prev[prev.length - 1].id }];
      }
      if (prev.length > 0 && prev[prev.length - 1].role === nextMessage.role && prev[prev.length - 1].body === content) {
        return prev;
      }
      return [...prev, nextMessage];
    });
  }, [docAutoSyncState, manualDocumentMarkdown]);

  useEkoSessionRealtime({ sessionId: data.id, onEnvelope: handleRealtimeEnvelope });

  const phase = agentSlice?.phase ?? "IDLE";
  const wsStatus = agentSlice?.wsStatus ?? "idle";
  const useMockFb = agentSlice?.useMockFallback ?? false;
  const docStream = agentSlice?.docMarkdownStream ?? "";
  const docConflict = agentSlice?.documentConflict ?? false;
  const lastErr = agentSlice?.lastError ?? null;
  const detailArtifact = localArtifact ?? data.artifact;
  const artifactTerminal = detailArtifact?.status === "done" || detailArtifact?.status === "completed" || detailArtifact?.status === "failed";
  const activeDocStream =
    agentSlice?.isDocStreaming &&
    Boolean(docStream) &&
    (phase === "ANALYZING" || phase === "RETRIEVING" || phase === "GENERATING" || phase === "SYNCING")
      ? docStream
      : "";
  const showDocStream =
    Boolean(activeDocStream) &&
    phase !== "COMPLETED" &&
    phase !== "ERROR" &&
    (!detailArtifact || agentSlice?.isDocStreaming || !artifactTerminal);
  const resourceArtifact = localArtifact ?? data.canvas.artifact ?? data.document.artifact ?? data.artifact;
  const resourceKind = normalizeArtifactKind(resourceArtifact);
  const renderedDocumentMarkdown = useMemo(() => sectionsToMarkdown(data.document.sections), [data.document.sections]);
  const baseDocumentMarkdown = activeDocStream || (localArtifact?.kind === "docx" ? localArtifact.content : null) || data.document.markdown;
  const documentMarkdown = manualDocumentMarkdown ?? baseDocumentMarkdown;
  const currentDocumentMarkdown = documentMarkdown || renderedDocumentMarkdown;
  const showDocumentSections = !detailArtifact;
  const canvasSurfaceArtifact = localArtifact ?? data.canvas.artifact ?? data.artifact;
  const showCanvasScaffold = normalizeArtifactKind(canvasSurfaceArtifact) !== "board";
  const resourceTab: DetailTabKey | null =
    resourceKind === "board" ? "canvas" : resourceKind === "ppt" || resourceKind === "docx" || showDocStream ? "doc" : null;
  const workspaceExpanded = resourceTab !== null;
  const displayTab = resourceTab ?? activeTab;
  const mergedWorkflow = useMemo(
    () => mergeWorkflowSteps(data.workflow, plannerEnabled ? agentSlice?.planningSteps ?? [] : [], resourceKind, phase, detailArtifact?.status),
    [agentSlice?.planningSteps, data.workflow, detailArtifact?.status, phase, plannerEnabled, resourceKind],
  );

  const handlePlannerToggle = useCallback(
    (nextEnabled: boolean) => {
      setPlannerEnabled(nextEnabled);
      if (!nextEnabled) {
        useAgentRuntimeStore.getState().patchSession(data.id, { planningPlan: null, planningSteps: [] });
      }
    },
    [data.id],
  );

  useEffect(() => {
    if (!data.artifact) return;
    const differentArtifact =
      data.artifact.jobId !== localArtifact?.jobId ||
      data.artifact.whiteboardId !== localArtifact?.whiteboardId ||
      data.artifact.kind !== localArtifact?.kind ||
      data.artifact.status !== localArtifact?.status ||
      data.artifact.content !== localArtifact?.content ||
      data.artifact.sharingUrl !== localArtifact?.sharingUrl ||
      data.artifact.currentStep !== localArtifact?.currentStep;
    if (!localArtifact || differentArtifact) {
      setLocalArtifact(data.artifact);
      if (data.artifact.kind === "docx") {
        setManualDocumentMarkdown(null);
        setDocAutoSyncState("idle");
        setDocAutoSyncError(null);
      }
    }
  }, [data.artifact, localArtifact]);

  useEffect(() => {
    return () => {
      if (docAutoSyncTimerRef.current) {
        clearTimeout(docAutoSyncTimerRef.current);
      }
      docAutoSyncAbortRef.current?.abort();
    };
  }, []);

  const handleManualDocumentChange = useCallback(
    (nextMarkdown: string) => {
      setManualDocumentMarkdown(nextMarkdown);
      setDocAutoSyncError(null);
      if (!nextMarkdown.trim()) {
        setDocAutoSyncState("idle");
        if (docAutoSyncTimerRef.current) {
          clearTimeout(docAutoSyncTimerRef.current);
          docAutoSyncTimerRef.current = null;
        }
        return;
      }

      setDocAutoSyncState("dirty");
      if (docAutoSyncTimerRef.current) {
        clearTimeout(docAutoSyncTimerRef.current);
      }
      const sequence = docAutoSyncSeqRef.current + 1;
      docAutoSyncSeqRef.current = sequence;
      const currentUrl = resourceArtifact?.sharingUrl ?? null;
      const title = resourceArtifact?.title || data.document.title || data.title || "Eko 文档";

      docAutoSyncTimerRef.current = setTimeout(async () => {
        docAutoSyncAbortRef.current?.abort();
        const controller = new AbortController();
        docAutoSyncAbortRef.current = controller;
        setDocAutoSyncState("syncing");
        try {
          const result = await fetchEkoJson<DocumentAutoSyncWire>("/api/v1/document/sync", {
            method: "POST",
            signal: controller.signal,
            body: JSON.stringify({
              session_id: data.id,
              title,
              content: nextMarkdown,
              current_url: currentUrl,
            }),
          });
          if (docAutoSyncSeqRef.current !== sequence) return;
          if (result.status === "failed") {
            throw new Error(result.message || "自动同步失败");
          }
          const nextArtifact: DetailDocumentArtifact = {
            ...(resourceArtifact ?? {}),
            kind: "docx",
            title,
            content: nextMarkdown,
            status: "completed",
            currentStep: "文档已自动同步",
            sharingUrl: result.document_url || currentUrl || resourceArtifact?.sharingUrl,
            resultSummary: result.message,
          };
          setLocalArtifact(nextArtifact);
          setManualDocumentMarkdown(null);
          setDocAutoSyncState("synced");
          setDocAutoSyncError(null);
          setRuntimeSessionPatch(data.id, { status: "已同步", updatedAt: "刚刚" });
        } catch (error) {
          if (controller.signal.aborted) return;
          if (docAutoSyncSeqRef.current !== sequence) return;
          setDocAutoSyncState("failed");
          setDocAutoSyncError(error instanceof Error ? error.message : "自动同步失败");
        }
      }, 1400);
    },
    [data.document.title, data.id, data.title, resourceArtifact, setRuntimeSessionPatch],
  );

  useEffect(() => {
    const status = (localArtifact?.status ?? "").toLowerCase();
    const kind = normalizeArtifactKind(localArtifact);
    if (!localArtifact || status === "done" || status === "completed" || status === "failed") return;
    if (kind === "docx") return;

    let cancelled = false;
    const poll = async () => {
      const session = await fetchSyncSession(data.id);
      if (cancelled || !session?.artifact) return;
      const nextArtifact = toDetailArtifact(session.artifact as AgentChatResponseWire["artifact"]);
      if (nextArtifact) setLocalArtifact(nextArtifact);
    };

    void poll();
    const timer = window.setInterval(poll, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [data.id, localArtifact]);

  const prevPhaseRef = useRef(phase);
  useEffect(() => {
    if (phase === "COMPLETED" && prevPhaseRef.current !== "COMPLETED") {
      const now = new Date();
      const hh = now.getHours().toString().padStart(2, "0");
      const mm = now.getMinutes().toString().padStart(2, "0");
      setRuntimeSessionPatch(data.id, { status: "已同步", updatedAt: `刚刚 ${hh}:${mm}` });
    }
    prevPhaseRef.current = phase;
  }, [phase, data.id, setRuntimeSessionPatch]);

  const handleChatSend = useCallback(
    async (text: string) => {
      const time = formatMessageTime();
      const requestId = Date.now();
      const userHistoryMessage = {
        id: `user-${requestId}`,
        author: "我",
        role: "member" as const,
        time,
        body: text,
        avatar: "我",
        sent: true,
      };
      setMessages((prev) => [
        ...prev,
        userHistoryMessage,
      ]);
      const chatHistory = [...messages, userHistoryMessage]
        .slice(-30)
        .map((message) => ({
          role: message.role === "eko" || message.author === "Eko" ? "assistant" : "user",
          content: message.body,
        }))
        .filter((message) => message.content.trim().length > 0);

      const streamMessageId = `eko-stream-${requestId}`;
      const store = useAgentRuntimeStore.getState();
      const isExistingDocumentEdit = resourceKind === "docx" && Boolean(currentDocumentMarkdown.trim()) && !wantsNewDocument(text);
      store.patchSession(data.id, { phase: "ANALYZING", lastError: null, useMockFallback: false });

      setSending(true);
      try {
        let streamError: string | null = null;
        const updateStreamMessage = (
          chunk: string,
          options: {
            helperText?: string;
            plannerCard?: PlanningPlanWire;
            sent?: boolean;
            replace?: boolean;
          } = {},
        ) => {
          setMessages((prev) => {
            const existingIndex = prev.findIndex((message) => message.id === streamMessageId);
            if (existingIndex === -1) {
              return [
                ...prev,
                {
                  id: streamMessageId,
                  author: "Eko",
                  role: "eko" as const,
                  time: formatMessageTime(),
                  body: chunk,
                  avatar: "E",
                  helperText: options.helperText,
                  plannerCard: options.plannerCard,
                  sent: options.sent,
                },
              ];
            }
            return prev.map((message, index) => {
              if (index !== existingIndex) return message;
              return {
                ...message,
                body: options.replace ? chunk || message.body : chunk ? `${message.body}${message.body ? "\n\n" : ""}${chunk}` : message.body,
                helperText: options.helperText,
                plannerCard: options.plannerCard ?? message.plannerCard,
                sent: options.sent ?? message.sent,
              };
            });
          });
        };

        const applyResponse = (response: AgentChatResponseWire) => {
          const nextArtifact = toDetailArtifact(response.artifact);
          const planningPlan = plannerEnabled ? toPlanningPlan(response.plan) : null;
          const planningSteps = planningPlan?.steps ?? [];
          if (nextArtifact) {
            setLocalArtifact(nextArtifact);
            setActiveTab(nextArtifact.kind === "board" ? "canvas" : "doc");
            store.patchSession(data.id, {
              phase: response.status === "failed" ? "ERROR" : response.status === "completed" ? "COMPLETED" : "GENERATING",
              intent: nextArtifact.kind === "ppt" ? "PPT" : nextArtifact.kind === "board" ? "CANVAS" : "DOC",
              planningPlan,
              planningSteps,
              lastError: response.error ?? nextArtifact.errorMessage ?? null,
              isDocStreaming: false,
              docMarkdownStream: "",
            });
          } else {
            store.patchSession(data.id, {
              phase: response.status === "failed" ? "ERROR" : "COMPLETED",
              intent: "CHAT",
              planningPlan,
              planningSteps,
              lastError: response.error ?? null,
            });
          }
          updateStreamMessage(response.status === "failed" ? response.message : isExistingDocumentEdit ? response.message : `已经完成。\n${response.message}`, {
            sent: true,
            replace: isExistingDocumentEdit,
          });
          if (response.status === "completed") {
            setRuntimeSessionPatch(data.id, { status: "已同步", updatedAt: "刚刚" });
          }
        };

        const streamed = await streamAgentChat(
          {
            session_id: data.id,
            message: text,
            current_document:
              resourceKind === "docx" && currentDocumentMarkdown
                ? {
                    kind: "docx",
                    content: currentDocumentMarkdown,
                    status: resourceArtifact?.status,
                    sharing_url: resourceArtifact?.sharingUrl,
                    result_summary: resourceArtifact?.resultSummary,
                  }
                : undefined,
            context: { chat_history: chatHistory },
            planning_enabled: isExistingDocumentEdit ? false : plannerEnabled,
          },
          (event: AgentChatStreamEvent) => {
            const payload = event.payload ?? {};
            store.patchSession(data.id, { useMockFallback: false });
            if (event.event === "turn.started") {
              const planningEnabled = payload.planning_enabled !== false;
              updateStreamMessage(isExistingDocumentEdit ? "好的，直接修改当前文档。" : event.message || "收到。我开始处理。", {
                helperText: planningEnabled ? "理解与规划中" : "直接执行中",
                replace: isExistingDocumentEdit,
              });
              return;
            }
            if (event.event === "intent.recognized") {
              store.patchSession(data.id, { phase: "ANALYZING" });
              if (isExistingDocumentEdit) return;
              const intent = typeof payload.intent === "string" ? payload.intent : "chat";
              updateStreamMessage(event.message || `我判断这次要走 ${intent} 能力。`, { sent: true });
              return;
            }
            if (event.event === "retrieval.started") {
              store.ingestEnvelope(data.id, event);
              if (isExistingDocumentEdit) return;
              updateStreamMessage(event.message || "正在检索 RAG 知识库。", { helperText: "RAG 检索中", replace: true });
              return;
            }
            if (event.event === "retrieval.completed") {
              store.ingestEnvelope(data.id, event);
              if (isExistingDocumentEdit) return;
              const sources = Array.isArray(payload.sources) ? payload.sources : [];
              updateStreamMessage(event.message || `已检索到 ${sources.length} 条 RAG 来源。`, { sent: true });
              return;
            }
            if (event.event === "plan.created") {
              const planningPlan = toPlanningPlan(payload.plan as AgentChatResponseWire["plan"]);
              if (planningPlan) {
                store.patchSession(data.id, {
                  phase: "RETRIEVING",
                  planningPlan,
                  planningSteps: planningPlan.steps,
                });
                updateStreamMessage(planningMessageBody(planningPlan), {
                  plannerCard: planningPlan,
                  sent: true,
                });
              }
              return;
            }
            if (event.event === "plan.summary") {
              if (isExistingDocumentEdit) return;
              updateStreamMessage(event.message ? `计划：${event.message}` : "计划已生成。", { sent: true });
              return;
            }
            if (event.event === "plan.step") {
              if (isExistingDocumentEdit) return;
              updateStreamMessage(event.message || "继续执行下一步。", { sent: true });
              return;
            }
            if (event.event === "clarification.requested") {
              store.patchSession(data.id, { phase: "COMPLETED" });
              const questions = Array.isArray(payload.questions) ? payload.questions.filter((item): item is string => typeof item === "string") : [];
              updateStreamMessage(
                questions.length
                  ? `执行前还需要补充这些信息：\n${questions.map((question, index) => `${index + 1}. ${question}`).join("\n")}`
                  : event.message || "执行前还需要补充关键信息。",
                { sent: true },
              );
              return;
            }
            if (event.event === "tool.started") {
              store.patchSession(data.id, { phase: "GENERATING" });
              updateStreamMessage(isExistingDocumentEdit ? "正在修改当前文档..." : event.message || "好的，我现在调用对应能力。", {
                sent: true,
                replace: isExistingDocumentEdit,
              });
              return;
            }
            if (event.event === "result.created") {
              applyResponse(payload.response as AgentChatResponseWire);
              return;
            }
            if (event.event === "turn.failed") {
              const error = typeof payload.error === "string" ? payload.error : "";
              streamError = error || event.message || "处理失败，请稍后重试。";
            }
          },
        );

        if (!streamed) {
          throw new Error("流式接口不可用");
        }
        if (streamError) {
          throw new Error(streamError);
        }
      } catch (error) {
        store.patchSession(data.id, { phase: "ERROR", lastError: error instanceof Error ? error.message : "处理失败" });
        setMessages((prev) => [
          ...prev,
          {
            id: `eko-error-${Date.now()}`,
            author: "Eko",
            role: "eko" as const,
            time: "刚刚",
            body: error instanceof Error ? error.message : "处理失败，请稍后重试。",
            avatar: "E",
            sent: true,
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [currentDocumentMarkdown, data.id, messages, plannerEnabled, resourceArtifact, resourceKind, setRuntimeSessionPatch],
  );

  const handleContextSelectionRun = useCallback(async () => {
    if (contextMessages.length === 0) return;
    const replayContextRunEvents = (
      response: AgentChatResponseWire | undefined,
      options: { skipContext?: boolean } = {},
    ) => {
      const events = Array.isArray(response?.events) ? response.events : [];
      if (!events.length) return;

      const replayMessageId = `eko-context-run-${Date.now()}`;
        const updateReplayMessage = (
          chunk: string,
          eventOptions: {
            helperText?: string;
            sent?: boolean;
            replace?: boolean;
          } = {},
        ) => {
        setMessages((prev) => {
          const existingIndex = prev.findIndex((message) => message.id === replayMessageId);
          if (existingIndex === -1) {
            return [
              ...prev,
                {
                  id: replayMessageId,
                  author: "Eko",
                  role: "eko" as const,
                  time: "刚刚",
                  body: chunk,
                  avatar: "E",
                  helperText: eventOptions.helperText,
                  sent: eventOptions.sent,
                },
              ];
            }
          return prev.map((message, index) => {
            if (index !== existingIndex) return message;
              return {
                ...message,
                body: eventOptions.replace ? chunk || message.body : chunk ? `${message.body}${message.body ? "\n\n" : ""}${chunk}` : message.body,
                helperText: eventOptions.helperText,
                sent: eventOptions.sent ?? message.sent,
              };
            });
          });
      };

      for (const event of events) {
        const payload = event.payload ?? {};
        if (event.event === "turn.started") {
          const message = options.skipContext
            ? "收到。本次将忽略群聊消息记录，直接继续处理。"
            : event.message || "收到。我开始处理。";
          updateReplayMessage(message, {
            helperText: payload.planning_enabled !== false ? "理解与规划中" : "直接执行中",
            replace: true,
          });
          continue;
        }
        if (event.event === "intent.recognized") {
          const intent = typeof payload.intent === "string" ? payload.intent : "chat";
          updateReplayMessage(event.message || `我判断这次要走 ${intent} 能力。`, { sent: true });
          continue;
        }
        if (event.event === "retrieval.started") {
          updateReplayMessage(event.message || "正在检索 RAG 知识库。", { helperText: "RAG 检索中", replace: true });
          continue;
        }
        if (event.event === "retrieval.completed") {
          const sources = Array.isArray(payload.sources) ? payload.sources : [];
          updateReplayMessage(event.message || `已检索到 ${sources.length} 条 RAG 来源。`, { sent: true });
          continue;
        }
          if (event.event === "plan.created") {
            const planningPlan = toPlanningPlan(payload.plan as AgentChatResponseWire["plan"]);
            if (planningPlan) {
              useAgentRuntimeStore.getState().patchSession(data.id, {
                phase: "RETRIEVING",
                planningPlan,
                planningSteps: planningPlan.steps,
                lastError: null,
              });
              updateReplayMessage(planningMessageBody(planningPlan), { sent: true });
            }
            continue;
          }
        if (event.event === "plan.summary") {
          updateReplayMessage(event.message ? `计划：${event.message}` : "计划已生成。", { sent: true });
          continue;
        }
        if (event.event === "plan.step") {
          updateReplayMessage(event.message || "继续执行下一步。", { sent: true });
          continue;
        }
        if (event.event === "clarification.requested") {
          const questions = Array.isArray(payload.questions) ? payload.questions.filter((item): item is string => typeof item === "string") : [];
          updateReplayMessage(
            questions.length
              ? `执行前还需要补充这些信息：\n${questions.map((question, index) => `${index + 1}. ${question}`).join("\n")}`
              : event.message || "执行前还需要补充关键信息。",
            { sent: true },
          );
          continue;
        }
        if (event.event === "tool.started") {
          updateReplayMessage(event.message || "好的，我现在调用对应能力。", { sent: true });
        }
      }
    };
    const startIndex = Math.min(contextStart, contextEnd);
    const endIndex = Math.max(contextStart, contextEnd);
    setContextSubmitting(true);
    setContextNotice(null);
    try {
      const response = await fetch(`/api/v1/sync/sessions/${encodeURIComponent(data.id)}/context/selection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start_index: startIndex, end_index: endIndex }),
      });
      const body = (await response.json().catch(() => null)) as { code?: number; data?: AgentChatResponseWire } | null;
      if (!response.ok || !body || body.code !== 0) {
        throw new Error("上下文提交失败");
      }
      replayContextRunEvents(body.data);
      const planningPlan = plannerEnabled ? toPlanningPlan(body.data?.plan) : null;
      if (planningPlan) {
        useAgentRuntimeStore.getState().patchSession(data.id, {
          phase: "COMPLETED",
          planningPlan,
          planningSteps: planningPlan.steps,
          lastError: null,
        });
      }
      setMessages((prev) => [
        ...prev,
        {
          id: `eko-context-${Date.now()}`,
          author: "Eko",
          role: "eko",
          time: "刚刚",
          body: [planningPlan ? planningMessageBody(planningPlan) : "", body.data?.message || "已基于选中的上下文生成回复。"].filter(Boolean).join("\n\n"),
          avatar: "E",
          sent: true,
        },
      ]);
      setContextNotice(`已提交第 ${startIndex + 1} 到 ${endIndex + 1} 条上下文`);
      setRuntimeSessionPatch(data.id, { status: "已同步", updatedAt: "刚刚" });
    } catch (error) {
      setContextNotice(error instanceof Error ? error.message : "上下文提交失败");
    } finally {
      setContextSubmitting(false);
    }
  }, [contextEnd, contextMessages.length, contextStart, data.id, plannerEnabled, setRuntimeSessionPatch]);

  const handleContextSkipRun = useCallback(async () => {
    setContextSubmitting(true);
    setContextNotice(null);
    try {
      const response = await fetch(`/api/v1/sync/sessions/${encodeURIComponent(data.id)}/context/selection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start_index: 0, end_index: 0, skip_context: true }),
      });
      const body = (await response.json().catch(() => null)) as { code?: number; data?: AgentChatResponseWire } | null;
      if (!response.ok || !body || body.code !== 0) {
        throw new Error("跳过上下文后生成失败");
      }
      const events = Array.isArray(body.data?.events) ? body.data.events : [];
      if (events.length) {
        const payload = body.data;
        const replayMessageId = `eko-context-run-${Date.now()}`;
        const updateReplayMessage = (
          chunk: string,
          options: {
            helperText?: string;
            sent?: boolean;
            replace?: boolean;
          } = {},
        ) => {
          setMessages((prev) => {
            const existingIndex = prev.findIndex((message) => message.id === replayMessageId);
            if (existingIndex === -1) {
              return [
                ...prev,
                {
                  id: replayMessageId,
                  author: "Eko",
                  role: "eko" as const,
                  time: "刚刚",
                  body: chunk,
                  avatar: "E",
                  helperText: options.helperText,
                  sent: options.sent,
                },
              ];
            }
            return prev.map((message, index) => {
              if (index !== existingIndex) return message;
              return {
                ...message,
                body: options.replace ? chunk || message.body : chunk ? `${message.body}${message.body ? "\n\n" : ""}${chunk}` : message.body,
                helperText: options.helperText,
                sent: options.sent ?? message.sent,
              };
            });
          });
        };
        for (const event of events) {
          const eventPayload = event.payload ?? {};
          if (event.event === "turn.started") {
            updateReplayMessage("收到。本次将忽略群聊消息记录，直接继续处理。", {
              helperText: eventPayload.planning_enabled !== false ? "理解与规划中" : "直接执行中",
              replace: true,
            });
            continue;
          }
          if (event.event === "intent.recognized") {
            const intent = typeof eventPayload.intent === "string" ? eventPayload.intent : "chat";
            updateReplayMessage(event.message || `我判断这次要走 ${intent} 能力。`, { sent: true });
            continue;
          }
          if (event.event === "retrieval.started") {
            updateReplayMessage(event.message || "正在检索 RAG 知识库。", { helperText: "RAG 检索中", replace: true });
            continue;
          }
          if (event.event === "retrieval.completed") {
            const sources = Array.isArray(eventPayload.sources) ? eventPayload.sources : [];
            updateReplayMessage(event.message || `已检索到 ${sources.length} 条 RAG 来源。`, { sent: true });
            continue;
          }
          if (event.event === "plan.created") {
            const planningPlan = toPlanningPlan(eventPayload.plan as AgentChatResponseWire["plan"]);
            if (planningPlan) {
              useAgentRuntimeStore.getState().patchSession(data.id, {
                phase: "RETRIEVING",
                planningPlan,
                planningSteps: planningPlan.steps,
                lastError: null,
              });
              updateReplayMessage(planningMessageBody(planningPlan), { sent: true });
            }
            continue;
          }
          if (event.event === "plan.summary") {
            updateReplayMessage(event.message ? `计划：${event.message}` : "计划已生成。", { sent: true });
            continue;
          }
          if (event.event === "plan.step") {
            updateReplayMessage(event.message || "继续执行下一步。", { sent: true });
            continue;
          }
          if (event.event === "clarification.requested") {
            const questions = Array.isArray(eventPayload.questions) ? eventPayload.questions.filter((item): item is string => typeof item === "string") : [];
            updateReplayMessage(
              questions.length
                ? `执行前还需要补充这些信息：\n${questions.map((question, index) => `${index + 1}. ${question}`).join("\n")}`
                : event.message || "执行前还需要补充关键信息。",
              { sent: true },
            );
            continue;
          }
          if (event.event === "tool.started") {
            updateReplayMessage(event.message || "好的，我现在调用对应能力。", { sent: true });
          }
        }
        const planningPlan = plannerEnabled ? toPlanningPlan(payload?.plan) : null;
        if (planningPlan) {
          useAgentRuntimeStore.getState().patchSession(data.id, {
            phase: "COMPLETED",
            planningPlan,
            planningSteps: planningPlan.steps,
            lastError: null,
          });
        }
      }
      const finalPlanningPlan = plannerEnabled ? toPlanningPlan(body.data?.plan) : null;
      setMessages((prev) => [
        ...prev,
        {
          id: `eko-context-skip-${Date.now()}`,
          author: "Eko",
          role: "eko",
          time: "刚刚",
          body: [finalPlanningPlan ? planningMessageBody(finalPlanningPlan) : "", body.data?.message || "已忽略群聊消息记录，直接生成回复。"].filter(Boolean).join("\n\n"),
          avatar: "E",
          sent: true,
        },
      ]);
      setContextNotice("已忽略上下文消息记录，直接开始生成");
      setRuntimeSessionPatch(data.id, { status: "已同步", updatedAt: "刚刚" });
    } catch (error) {
      setContextNotice(error instanceof Error ? error.message : "跳过上下文后生成失败");
    } finally {
      setContextSubmitting(false);
    }
  }, [data.id, plannerEnabled, setRuntimeSessionPatch]);

  function prependCanvasActivity(title: string, tone: DetailActivity["tone"]) {
    setCanvasActivities((prev) => [
      {
        id: `${title}-${Date.now()}`,
        title,
        time: "刚刚",
        tone,
      },
      ...prev,
    ]);
  }

  function handleAddNode() {
    setCanvasNodes((prev) => {
      const nextIndex = prev.length + 1;
      return [
        ...prev,
        {
          id: `canvas-node-${nextIndex}`,
          index: nextIndex,
          title: "新增节点",
          bullets: ["待补充要点", "可由 Eko 自动生成"],
          icon: "spark",
          status: "draft",
        },
      ];
    });
    setCanvasNotice("已添加新节点，可继续让 Eko 补充内容。");
    prependCanvasActivity("新增画布节点", "route");
  }

  function handleConfirmSave() {
    setBitableStatus("completed");
    setArchiveStatus("已归档");
    setPermissionStatus("已确认");
    setCanvasNotice("已确认保存，Bitable 同步状态已更新。");
    prependCanvasActivity("画布已确认保存", "data");
  }

  function handleConversationAction(label: string) {
    if (label === "确认保存") {
      handleConfirmSave();
      return;
    }
    if (label === "打开工作台") {
      setCanvasNotice("工作台已打开，可继续查看画布与同步状态。");
      prependCanvasActivity("打开工作台查看进度", "session");
      return;
    }
    if (label === "查看进度") {
      setCanvasNotice("当前画布生成进度已更新。");
      prependCanvasActivity("查看画布生成进度", "route");
    }
  }

  function cycleOutputTab() {
    setActiveTab((current) => (current === "doc" ? "canvas" : "doc"));
    setCanvasNotice("已切换输出视图。");
  }

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden overflow-x-hidden bg-[#FAFBFC] text-slate-900">
      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-5 pb-5 pt-2 sm:px-6 sm:pb-6 sm:pt-3">
          <div className="flex h-full min-h-0 min-w-0 gap-4 overflow-hidden lg:gap-5">
              <div
                className={[
                  "min-h-0 overflow-hidden transition-[width,opacity,transform] duration-300 ease-out",
                  workspaceExpanded
                    ? conversationOpen
                      ? "w-[260px] opacity-100"
                      : "pointer-events-none w-0 -translate-x-4 opacity-0"
                    : "w-full flex-1 opacity-100",
                ].join(" ")}
              >
                <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-[28px] border border-slate-200/90 bg-white px-5 py-4 shadow-[0_14px_32px_rgba(148,163,184,0.08)]">
                  <div className="flex items-center justify-between">
                    <h2 className="text-[17px] font-semibold text-slate-950">{data.conversationTitle}</h2>
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => setConversationFilter((current) => (current === "all" ? "eko" : "all"))}
                        className={[
                          "rounded-full border p-1.5 transition",
                          conversationFilter === "eko"
                            ? "border-blue-200 bg-blue-50 text-blue-600"
                            : "border-transparent text-slate-500 hover:bg-slate-50",
                        ].join(" ")}
                        aria-label={conversationFilter === "eko" ? "显示全部对话" : "只看 Eko 回复"}
                        title={conversationFilter === "eko" ? "显示全部对话" : "只看 Eko 回复"}
                      >
                        <SmallIcon type="filter" tone="slate" />
                      </button>
                      <button
                        type="button"
                        onClick={cycleOutputTab}
                        className="rounded-full border border-transparent p-1.5 hover:bg-slate-50"
                        aria-label="切换输出视图"
                        title="切换输出视图"
                      >
                        <MoreIcon />
                      </button>
                    </div>
                  </div>
                  <div className="mt-4 min-h-0 flex-1 border-t border-slate-100 pt-4">
                    <div className="flex h-full min-h-0 flex-col">
                      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
                        {filteredMessages.length === 0 && searchNeedle ? (
                          <p className="text-center text-[13px] text-slate-400">没有匹配的对话内容</p>
                        ) : null}
                        {filteredMessages.map((message, msgIdx) => (
                          <DetailConversationMessage
                            key={message.id ?? `msg-${msgIdx}`}
                            message={message}
                            selfAuthor={selfAuthor}
                            tone={conversationTone}
                            onActionButtonClick={isCanvasMode ? handleConversationAction : undefined}
                          />
                        ))}
                      </div>
                      <div className="mt-4 shrink-0">
                        <MessageInput
                          sessionId={data.id}
                          tone={conversationTone}
                          placeholder="继续让 Eko 处理…"
                          onSend={handleChatSend}
                          disabled={sending}
                        />
                      </div>
                    </div>
                  </div>
                </section>
              </div>

              {workspaceExpanded ? (
                <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
                    <section className="min-h-0 flex flex-1 flex-col overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-[0_10px_22px_rgba(148,163,184,0.05)]">
                      <div className="shrink-0 border-b border-slate-100 bg-white px-3 py-1">
                          <div className="flex min-h-[70px] min-w-0 flex-col overflow-hidden rounded-[14px] border border-slate-200 bg-white px-3 py-1.5 shadow-[0_4px_12px_rgba(15,23,42,0.03)]">
                            <div className="flex shrink-0 items-center justify-between gap-3">
                              <AgentRealtimeRibbon phase={phase} wsStatus={wsStatus} useMockFallback={useMockFb} />
                              {lastErr ? (
                                <p className="shrink-0 text-[10px] font-medium text-rose-600">生成失败：{lastErr}</p>
                              ) : (
                                <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                                  <button
                                    type="button"
                                    role="switch"
                                    aria-checked={plannerEnabled}
                                    onClick={() => handlePlannerToggle(!plannerEnabled)}
                                    className={[
                                      "inline-flex h-7 shrink-0 items-center gap-2 rounded-full border px-2 text-[10px] font-semibold transition-colors",
                                      plannerEnabled
                                        ? "border-blue-200 bg-blue-50 text-blue-700"
                                        : "border-slate-200 bg-slate-50 text-slate-500",
                                    ].join(" ")}
                                  >
                                    <span className={`relative h-3.5 w-6 rounded-full transition-colors ${plannerEnabled ? "bg-blue-600" : "bg-slate-300"}`} aria-hidden>
                                      <span className={`absolute top-0.5 h-2.5 w-2.5 rounded-full bg-white transition-transform ${plannerEnabled ? "translate-x-3" : "translate-x-0.5"}`} />
                                    </span>
                                    任务理解与规划
                                  </button>
                                  <StepperStatusLegend />
                                </div>
                              )}
                            </div>
                            <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden">
                              <Stepper steps={mergedWorkflow} className="mt-0" />
                            </div>
                          </div>
                        </div>
                      <div className="min-h-0 flex-1 overflow-hidden bg-white">
                        <AnimatePresence mode="wait">
                          {displayTab === "doc" ? (
                            <motion.div key="doc-tab" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }} className="flex h-full min-h-0 flex-col">
                            {docConflict ? (
                              <div className="shrink-0 border-b border-amber-100 bg-amber-50 px-4 py-2 text-[11px] text-amber-900">
                                检测到服务端文稿版本与本地草稿可能冲突，请以服务端为准或稍后刷新。
                              </div>
                            ) : null}
                            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
                              <div className="space-y-[14px] pb-8">
	                                <ArtifactPresenter
	                                  artifact={localArtifact ?? data.document.artifact ?? data.artifact}
	                                  sessionId={data.id}
	                                  markdown={documentMarkdown}
	                                  sections={data.document.sections}
                                    streaming={showDocStream}
                                    editable={resourceKind === "docx" && !showDocStream}
                                    onMarkdownChange={handleManualDocumentChange}
                                    autoSyncState={docAutoSyncState}
                                    autoSyncError={docAutoSyncError}
	                                />
                                {showDocumentSections ? data.document.sections.map((section, secIdx) => (
                                  <section key={`doc-${secIdx}-${section.title}`}>
                                    <h4 className="text-[14px] font-semibold text-slate-950">{section.title}</h4>
                                    {section.body ? (
                                      <div className="prose prose-sm mt-2 max-w-none text-slate-700 prose-headings:my-2 prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0.5">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.body}</ReactMarkdown>
                                      </div>
                                    ) : null}
                                    {section.bullets ? (
                                      <div className="prose prose-sm mt-2 max-w-none text-slate-700 prose-ul:my-1.5 prose-li:my-0.5">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                          {section.bullets.map((item) => `- ${item}`).join("\n")}
                                        </ReactMarkdown>
                                      </div>
                                    ) : null}
                                    {section.title === "活动表现" && data.document.tableRows ? (
                                      <div className="mt-3 min-w-0 overflow-x-auto rounded-[16px] border border-slate-200">
                                        <table className="w-full border-collapse text-left text-[12px]">
                                          <thead className="bg-slate-50 text-slate-500">
                                            <tr>
                                              <th className="px-[14px] py-2 font-medium">活动名称</th>
                                              <th className="px-[14px] py-2 font-medium">渠道</th>
                                              <th className="px-[14px] py-2 font-medium">访问量</th>
                                              <th className="px-[14px] py-2 font-medium">线索数</th>
                                              <th className="px-[14px] py-2 font-medium">转化率</th>
                                              <th className="px-[14px] py-2 font-medium">ROI</th>
                                              <th className="px-[14px] py-2 font-medium">消耗预算</th>
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {data.document.tableRows.map((row, ri) => (
                                              <tr key={`${row.campaign}-${ri}`} className="border-t border-slate-100 text-slate-700">
                                                <td className="px-[14px] py-2">{row.campaign}</td>
                                                <td className="px-[14px] py-2">{row.channel}</td>
                                                <td className="px-[14px] py-2">{row.visits}</td>
                                                <td className="px-[14px] py-2">{row.leads}</td>
                                                <td className="px-[14px] py-2">{row.conversion}</td>
                                                <td className="px-[14px] py-2">{row.roi}</td>
                                                <td className="px-[14px] py-2">{row.budget}</td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    ) : null}
                                  </section>
                                )) : null}
                              </div>
                            </div>
                            </motion.div>
                          ) : (
                            <motion.div key="canvas-tab" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }} className="min-h-0 h-full overflow-y-auto px-3 pb-3 pt-1">
                            <ArtifactPresenter
                              artifact={canvasSurfaceArtifact}
                              sessionId={data.id}
                              markdown={data.document.markdown}
                              sections={data.document.sections}
                              streaming={false}
                            />
                            {showCanvasScaffold ? (
                              <>
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0 mt-3">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Output Surface</p>
                                <h3 className="mt-0.5 text-[15px] font-semibold text-slate-950">Canvas Preview</h3>
                                <p className="mt-0.5 line-clamp-1 text-[11px] text-slate-500">实时画板区域，保留节点预览与打开真实画布入口。</p>
                              </div>
                              <div className="mt-3 flex shrink-0 items-center gap-2">
                                <Link
                                  href={data.canvas.artifact?.sharingUrl || `/canvas?session=${encodeURIComponent(data.id)}`}
                                  prefetch={false}
                                  className="inline-flex h-8 items-center gap-1.5 rounded-[10px] border border-violet-200 bg-violet-50 px-2.5 text-[12px] font-semibold text-violet-600 shadow-[0_6px_16px_rgba(139,92,246,0.08)] transition hover:bg-violet-100"
                                >
                                  打开画布
                                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                                    <path d="M6 4H12V10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                    <path d="M11.5 4.5L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                                  </svg>
                                </Link>
                              </div>
                            </div>
                            <p className="mt-1.5 line-clamp-2 text-[11px] leading-snug text-slate-500">
                              进入全屏画布后，在浏览器视口<strong className="font-semibold text-slate-700">最顶端深色导航栏右侧</strong>
                              点击紫色「Agent 生长演示」，将按本会话的 mock 画布节点模拟远端推送并逐笔绘制。
                            </p>

                            <AnimatePresence>
                              {canvasNotice ? (
                                <motion.div
                                  initial={{ opacity: 0, y: -6 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  exit={{ opacity: 0, y: -8 }}
                                  className="mt-1.5 rounded-[14px] border border-violet-200 bg-violet-50 px-3 py-2 text-[12px] font-medium leading-snug text-violet-700 shadow-[0_6px_16px_rgba(139,92,246,0.08)]"
                                >
                                  {canvasNotice}
                                </motion.div>
                              ) : null}
                            </AnimatePresence>

                            <div className="mt-1.5 rounded-[16px] border border-violet-100 bg-[radial-gradient(circle_at_top,#FBF9FF_0%,#F8FAFF_45%,#FFFFFF_100%)] px-2 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
                              <div className="grid grid-cols-[minmax(0,1fr)_12px_minmax(0,1fr)_12px_minmax(0,1fr)] items-stretch gap-y-1.5">
                                {topRowNodes.map((node, idx) => (
                                  <div key={`top-${node.id}`} className="contents">
                                    <CanvasNodeCard
                                      index={node.index}
                                      title={node.title}
                                      bullets={node.bullets}
                                      icon={node.icon}
                                      status={node.status}
                                    />
                                    {idx < topRowNodes.length - 1 ? (
                                      <div className="flex justify-center text-slate-300">
                                        <svg width="14" height="10" viewBox="0 0 18 12" fill="none" aria-hidden="true">
                                          <path d="M1 6H14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                                          <path d="M11.2 2.7L14.7 6L11.2 9.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                      </div>
                                    ) : null}
                                  </div>
                                ))}
                                <div className="col-span-5 flex justify-center py-0">
                                  <div className="relative w-[71%] border-t border-dashed border-slate-300">
                                    <span className="absolute left-[16.6%] top-[-1px] h-3 border-l border-dashed border-slate-300" />
                                    <span className="absolute right-[16.6%] top-[-1px] h-3 border-l border-dashed border-slate-300" />
                                  </div>
                                </div>
                                {bottomRowNodes.map((node, idx) => (
                                  <div key={`bottom-${node.id}`} className="contents">
                                    <CanvasNodeCard
                                      index={node.index}
                                      title={node.title}
                                      bullets={node.bullets}
                                      icon={node.icon}
                                      status={node.status}
                                    />
                                    {idx < bottomRowNodes.length - 1 ? (
                                      <div className="flex justify-center text-slate-300">
                                        <svg width="14" height="10" viewBox="0 0 18 12" fill="none" aria-hidden="true">
                                          <path d="M1 6H14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                                          <path d="M11.2 2.7L14.7 6L11.2 9.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                      </div>
                                    ) : null}
                                  </div>
                                ))}
                              </div>

                              {canvasNodes.length > 6 ? (
                                <div className="mt-2 grid gap-2 md:grid-cols-3">
                                  {canvasNodes.slice(6).map((node) => (
                                    <CanvasNodeCard key={node.id} index={node.index} title={node.title} bullets={node.bullets} icon={node.icon} status={node.status} />
                                  ))}
                                  {canvasNodes.length === 7 ? (
                                    <button
                                      type="button"
                                      onClick={handleAddNode}
                                      className="flex min-h-[96px] items-center justify-center rounded-[16px] border border-dashed border-violet-200 bg-violet-50/40 text-[12px] font-semibold text-violet-500 transition hover:bg-violet-50"
                                    >
                                      + 继续添加节点
                                    </button>
                                  ) : null}
                                </div>
                              ) : null}
                            </div>

                            <div className="mt-2.5 grid gap-2 md:grid-cols-3">
                              <div className="rounded-[14px] border border-slate-200 bg-slate-50 px-2.5 py-2">
                                <p className="text-[10px] font-semibold tracking-[0.14em] text-slate-400">INPUT</p>
                                <p className="mt-1 text-[11px] text-slate-700">Feishu group discussion</p>
                              </div>
                              <div className="rounded-[14px] border border-slate-200 bg-slate-50 px-2.5 py-2">
                                <p className="text-[10px] font-semibold tracking-[0.14em] text-slate-400">AGENT</p>
                                <p className="mt-1 text-[11px] text-slate-700">Intent routing + RAG + generation</p>
                              </div>
                              <div className="rounded-[14px] border border-slate-200 bg-slate-50 px-2.5 py-2">
                                <p className="text-[10px] font-semibold tracking-[0.14em] text-slate-400">OUTPUT</p>
                                <p className="mt-1 text-[11px] text-slate-700">Canvas preview + synced project record</p>
                              </div>
                            </div>
                              </>
                            ) : null}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </section>
                </div>
              ) : null}

              <aside className="min-h-0 w-[250px] shrink-0 space-y-3 overflow-y-auto pr-1 lg:w-[270px]">
                    {isCanvasMode ? (
                      <>
                        <SectionCard title="上下文与同步" action={<MoreIcon />}>
                          <div className="space-y-4">
                            <div>
                              <h4 className="text-[14px] font-semibold text-slate-950">上下文来源</h4>
                              <div className="mt-3 space-y-3">
                                {filteredContextSources.length === 0 && searchNeedle ? (
                                  <p className="text-[12px] text-slate-400">没有匹配的上下文来源</p>
                                ) : null}
                                {filteredContextSources.map((item, index) => {
                                  const srcIndex = runtimeContextSources.findIndex((s) => s.id === item.id);
                                  const iconIdx = srcIndex >= 0 ? srcIndex : index;
                                  return (
                                  <div key={item.id} className={`flex min-w-0 items-start justify-between gap-3 rounded-[18px] border border-slate-200 bg-white px-3 py-2.5 ${index > 0 ? "" : ""}`}>
                                    <div className="flex min-w-0 flex-1 items-start gap-3">
                                      <div className="mt-[2px] flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-[9px] border border-slate-200 bg-white">
                                        <SmallIcon type={iconIdx === 0 ? "chat" : iconIdx === 1 ? "doc" : "sheet"} tone={iconIdx === 2 ? "orange" : "blue"} />
                                      </div>
                                      <div className="min-w-0 flex-1">
                                        <p className="truncate text-[13px] font-semibold text-slate-900">{item.title}</p>
                                        <p className="mt-1 break-words text-[12px] leading-[18px] text-slate-500">{item.description}</p>
                                      </div>
                                    </div>
                                    <div className="mt-[1px] shrink-0 self-start">
                                      <StatusPill status={item.status} />
                                    </div>
                                  </div>
                                  );
                                })}
                              </div>
                            </div>

                            <div>
                              <h4 className="text-[14px] font-semibold text-slate-950">来源证据</h4>
                              <div className="mt-3 space-y-3">
                                {runtimeSourceEvidence.map((item) => (
                                  <div key={item.id} className="flex min-w-0 items-start justify-between gap-3 rounded-[18px] border border-slate-200 bg-white px-3 py-2.5">
                                    <div className="flex min-w-0 items-start gap-3">
                                      <div className="mt-[2px] flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-[9px] border border-slate-200 bg-white">
                                        <SmallIcon type={item.tone === "chat" ? "chat" : item.tone === "document" ? "doc" : "sheet"} tone={item.tone === "chat" ? "green" : item.tone === "document" ? "blue" : "purple"} />
                                      </div>
                                      <div className="min-w-0">
                                        <p className="truncate text-[13px] font-semibold text-slate-900">{item.title}</p>
                                        <p className="mt-1 break-words text-[12px] leading-[18px] text-slate-500">{item.description}</p>
                                      </div>
                                    </div>
                                    <div className="mt-[1px] shrink-0 self-start">
                                      <EvidencePill tone={item.tone}>{item.tone === "chat" ? "聊天" : item.tone === "document" ? "文稿" : "数据"}</EvidencePill>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div>
                              <h4 className="text-[14px] font-semibold text-slate-950">同步动作</h4>
                              <div className="mt-3 space-y-3">
                                {canvasSyncActions.map((item) => (
                                  <div key={item.id} className="flex min-w-0 items-center justify-between gap-3 rounded-[18px] border border-slate-200 bg-white px-3 py-2.5">
                                    <div className="flex min-w-0 items-center gap-3">
                                      <div className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-[9px] border border-slate-200 bg-white">
                                        <SmallIcon type={item.id.includes("Bitable") || item.id.includes("ca1") ? "sync" : item.id.includes("待办") || item.id.includes("ca3") ? "check" : "share"} tone={item.status === "warning" ? "orange" : item.status === "running" ? "blue" : "slate"} />
                                      </div>
                                      <p className="truncate text-[13px] font-medium text-slate-800">{item.title}</p>
                                    </div>
                                    <div className="mt-[1px] shrink-0">
                                      <StatusPill status={item.status} />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </SectionCard>
                        <SectionCard title="同步状态" action={<HeaderBadge tone={bitableStatus === "completed" ? "success" : bitableStatus === "warning" ? "neutral" : "info"}>{bitableStatus === "completed" ? "已同步" : bitableStatus === "warning" ? "待确认" : "进行中"}</HeaderBadge>}>
                          <div className="space-y-3 text-[13px] text-slate-600">
                            <div className="flex items-center justify-between gap-3">
                              <span>多维表格状态</span>
                              <StatusPill status={bitableStatus === "completed" ? "completed" : bitableStatus === "warning" ? "warning" : "running"}>
                                {bitableStatus === "completed" ? "已同步" : bitableStatus === "warning" ? "预警" : "进行中"}
                              </StatusPill>
                            </div>
                          </div>
                        </SectionCard>
                        <SectionCard title="Bitable 归档状态">
                          <div className="flex items-center justify-between gap-3 text-[13px] text-slate-600">
                            <span>当前归档状态</span>
                            <span className="rounded-full bg-slate-100 px-3 py-1 text-[12px] font-semibold text-slate-500">{archiveStatus}</span>
                          </div>
                        </SectionCard>
                        <SectionCard title="权限状态">
                          <div className="flex items-center justify-between gap-3 text-[13px] text-slate-600">
                            <span>当前同步权限</span>
                            <span className="rounded-full bg-violet-50 px-3 py-1 text-[12px] font-semibold text-violet-600">{permissionStatus}</span>
                          </div>
                        </SectionCard>
                        <SectionCard title="状态">
                          <div className="flex flex-wrap gap-2">
                            {data.statusBadges.map((badge, bi) => (
                              <HeaderBadge key={`badges-${bi}-${badge.label}`} tone={badge.tone}>
                                {badge.label}
                              </HeaderBadge>
                            ))}
                          </div>
                        </SectionCard>
                        <SectionCard title="活动记录">
                          <div className="space-y-2.5">
                            {canvasActivities.map((item) => (
                              <ActivityRow key={item.id} item={item} />
                            ))}
                          </div>
                        </SectionCard>
                        <SectionCard title="系统说明">
                          <p className="text-[13px] leading-6 text-slate-600">{data.systemNote}</p>
                        </SectionCard>
                      </>
                    ) : (
                      <>
                        <SectionCard title="上下文来源">
                          <div className="space-y-3">
                            {filteredContextSources.length === 0 && searchNeedle ? (
                              <p className="text-[13px] text-slate-400">没有匹配的上下文来源</p>
                            ) : null}
                            {filteredContextSources.map((item, index) => {
                              const srcIndex = runtimeContextSources.findIndex((s) => s.id === item.id);
                              const iconIdx = srcIndex >= 0 ? srcIndex : index;
                              return (
                              <div
                                key={item.id}
                                className={`flex min-w-0 items-start justify-between gap-3 ${index > 0 ? "border-t border-slate-100 pt-3" : ""}`}
                              >
                                <div className="flex min-w-0 flex-1 items-start gap-3">
                                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[11px] border border-slate-200 bg-white">
                                    <SmallIcon type={iconIdx === 0 ? "sheet" : iconIdx === 1 ? "doc" : "sheet"} tone={iconIdx === 2 ? "green" : "blue"} />
                                  </div>
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate text-[14px] font-semibold text-slate-900">{item.title}</p>
                                    <p className="mt-1 break-words text-[12px] leading-5 text-slate-500">{item.description}</p>
                                  </div>
                                </div>
                                <div className="shrink-0 self-start">
                                  <StatusPill status={item.status} />
                                </div>
                              </div>
                              );
                            })}
                            {data.intent === "chat" && data.contextSources.some((item) => item.title.includes("最近群聊上下文")) ? (
                              <div className="rounded-[14px] border border-emerald-200 bg-emerald-50/70 px-3 py-2.5 text-[12px] leading-5 text-emerald-700">
                                普通对话已自动使用最近 15 条群聊上下文，无需手动选择消息记录。
                              </div>
                            ) : null}
                            {shouldShowContextSelector ? (
                              <div className="rounded-[14px] border border-slate-200 bg-slate-50/60">
                                <button
                                  type="button"
                                  onClick={() => setContextExpanded((open) => !open)}
                                  className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
                                >
                                  <div className="min-w-0">
                                    <p className="text-[13px] font-semibold text-slate-900">候选群聊消息</p>
                                    <p className="mt-0.5 text-[12px] text-slate-500">
                                      已读取 {contextMessages.length} 条，可选择连续范围进入 prompt。
                                    </p>
                                  </div>
                                  <span className="shrink-0 text-[12px] font-semibold text-blue-600">
                                    {contextExpanded ? "收起" : "展开"}
                                  </span>
                                </button>
                                {contextExpanded ? (
                                  <div className="border-t border-slate-200 px-3 pb-3 pt-2">
                                    <div className="grid grid-cols-2 gap-2">
                                      <label className="text-[12px] font-medium text-slate-600">
                                        起始
                                        <select
                                          value={contextStart}
                                          onChange={(event) => setContextStart(Number(event.target.value))}
                                          className="mt-1 h-9 w-full rounded-[10px] border border-slate-200 bg-white px-2 text-[12px] text-slate-700"
                                        >
                                          {contextMessages.map((_, index) => (
                                            <option key={`start-${index}`} value={index}>
                                              第 {index + 1} 条
                                            </option>
                                          ))}
                                        </select>
                                      </label>
                                      <label className="text-[12px] font-medium text-slate-600">
                                        结束
                                        <select
                                          value={contextEnd}
                                          onChange={(event) => setContextEnd(Number(event.target.value))}
                                          className="mt-1 h-9 w-full rounded-[10px] border border-slate-200 bg-white px-2 text-[12px] text-slate-700"
                                        >
                                          {contextMessages.map((_, index) => (
                                            <option key={`end-${index}`} value={index}>
                                              第 {index + 1} 条
                                            </option>
                                          ))}
                                        </select>
                                      </label>
                                    </div>
                                    <div className="mt-3 max-h-[320px] space-y-1.5 overflow-y-auto pr-1">
                                      {contextMessages.map((message, index) => {
                                        const startIndex = Math.min(contextStart, contextEnd);
                                        const endIndex = Math.max(contextStart, contextEnd);
                                        const selected = index >= startIndex && index <= endIndex;
                                        const time = message.timestamp
                                          ? new Date(message.timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
                                          : "";
                                        return (
                                          <button
                                            key={`${message.timestamp ?? index}-${index}`}
                                            type="button"
                                            onClick={() => {
                                              if (index < startIndex) setContextStart(index);
                                              else if (index > endIndex) setContextEnd(index);
                                              else {
                                                setContextStart(index);
                                                setContextEnd(index);
                                              }
                                            }}
                                            className={[
                                              "grid w-full grid-cols-[34px_minmax(0,1fr)] gap-2 rounded-[10px] border px-2.5 py-2 text-left text-[12px] transition",
                                              selected ? "border-blue-200 bg-blue-50 text-slate-900" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300",
                                            ].join(" ")}
                                          >
                                            <span className="pt-0.5 text-[11px] font-semibold text-slate-400">{index + 1}</span>
                                            <span className="min-w-0">
                                              <span className="mb-1 flex items-center gap-2 text-[11px] text-slate-400">
                                                <span>{message.role === "eko" ? "Eko" : "成员"}</span>
                                                {time ? <span>{time}</span> : null}
                                              </span>
                                              <span className="line-clamp-2 leading-5">{message.content}</span>
                                            </span>
                                          </button>
                                        );
                                      })}
                                    </div>
                                    <div className="mt-3 flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
                                      <p className="min-w-0 text-[12px] text-slate-500">
                                        选择 {Math.abs(contextEnd - contextStart) + 1} 条消息
                                      </p>
                                      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
                                        <button
                                          type="button"
                                          onClick={handleContextSkipRun}
                                          disabled={contextSubmitting}
                                          className="inline-flex h-9 items-center justify-center whitespace-nowrap rounded-[10px] border border-slate-200 bg-white px-3 text-[12px] font-semibold text-slate-600 disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
                                        >
                                          {contextSubmitting ? "处理中..." : "不使用上下文"}
                                        </button>
                                        <button
                                          type="button"
                                          onClick={handleContextSelectionRun}
                                          disabled={contextSubmitting}
                                          className="inline-flex h-9 items-center justify-center whitespace-nowrap rounded-[10px] bg-blue-600 px-3 text-[12px] font-semibold text-white disabled:bg-slate-300"
                                        >
                                          {contextSubmitting ? "处理中..." : "用选中上下文生成"}
                                        </button>
                                      </div>
                                    </div>
                                    {contextNotice ? <p className="mt-2 text-[12px] text-slate-500">{contextNotice}</p> : null}
                                  </div>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        </SectionCard>
                        <SectionCard title="关联文件" action={<span className="text-[12px] text-slate-400">查看全部（7）</span>}>
                          <div className="space-y-2.5">
                            {data.relatedFiles?.map((file) => (
                              <RelatedFileCard key={file.id} file={file} />
                            ))}
                          </div>
                        </SectionCard>
                        <SectionCard title="AI 记忆与上下文">
                          <div className="flex items-start gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-blue-50">
                              <SmallIcon type="memory" tone="blue" />
                            </div>
                            <div className="min-w-0">
                              <p className="break-words text-[13px] leading-6 text-slate-600">{data.memoryNote?.body}</p>
                              <button
                                type="button"
                                onClick={() => setMemoryExpanded((open) => !open)}
                                className="mt-3 text-[13px] font-semibold text-blue-600"
                              >
                                {memoryExpanded ? "收起记忆上下文" : data.memoryNote?.action}
                              </button>
                              {memoryExpanded ? (
                                <div className="mt-3 rounded-[14px] border border-blue-100 bg-blue-50/60 px-3 py-2 text-[12px] leading-5 text-slate-600">
                                  <p>已关联 {runtimeContextSources.length} 个上下文来源、{runtimeSourceEvidence.length} 条来源证据。</p>
                                  <p className="mt-1 text-slate-500">可用顶部搜索框筛选对话、上下文来源与证据。</p>
                                </div>
                              ) : null}
                            </div>
                          </div>
                        </SectionCard>
                        <SectionCard title="同步状态" action={<HeaderBadge tone="success">{data.syncOverview?.statusLabel}</HeaderBadge>}>
                          <div className="space-y-2.5">
                            {data.syncOverview?.items.map((item, syncIdx) => (
                              <div key={`sync-${syncIdx}-${item.slice(0, 40)}`} className="flex items-center gap-3 text-[13px] text-slate-600">
                                <SmallIcon type="sync" tone="blue" />
                                {item}
                              </div>
                            ))}
                          </div>
                        </SectionCard>
                        <SectionCard title="活动记录">
                          <div className="space-y-2.5">
                            {data.activities?.map((item) => (
                              <ActivityRow key={item.id} item={item} />
                            ))}
                          </div>
                        </SectionCard>
                      </>
                    )}
              </aside>
            </div>
          </section>
        </div>
    </div>
  );
}
