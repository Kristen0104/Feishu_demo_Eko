"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { MessageInput } from "@/components/MessageInput";
import { MoreIcon } from "@/components/Icons";
import { EvidencePill, HeaderBadge, StatusPill } from "@/components/UiPrimitives";
import { useEkoSessionRealtime } from "@/hooks/useEkoSessionRealtime";
import { streamAgentExecute, streamDocumentGeneration } from "@/lib/agent/sse-stream";
import { useAppStore } from "@/store/app-store";
import { useAgentRuntimeStore, type PlanningStepWire } from "@/store/agent-runtime-store";
import { Stepper } from "@/components/Stepper";
import { DetailActivity, DetailCanvasNode, DetailRelatedFile, DetailSyncAction, DetailTabKey, SessionDetailData } from "@/types/session-detail";
import type { WorkflowStatus, WorkflowStep } from "@/types/workspace";

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
      className="mt-2 flex shrink-0 flex-wrap gap-x-3 gap-y-1 border-t border-slate-100 pt-2 text-[10px] leading-tight text-slate-500"
    >
      <span className="inline-flex items-center gap-1">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" aria-hidden />
        已完成
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" aria-hidden />
        进行中
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300" aria-hidden />
        待处理
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" aria-hidden />
        预警
      </span>
    </div>
  );
}

function mergeWorkflowSteps(base: WorkflowStep[], live: PlanningStepWire[]): WorkflowStep[] {
  if (!live.length) return base;
  return live.map((s) => ({
    id: s.id,
    title: s.title,
    status: s.status,
  }));
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
      className="mb-1 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-600"
    >
      <span className="rounded-full bg-slate-900 px-2 py-0.5 font-semibold tracking-tight text-white">{phase}</span>
      <span className="text-slate-500">
        实时链路 {wsStatus}
        {useMockFallback ? " · 协议 mock" : ""}
      </span>
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
  const [activeTab, setActiveTab] = useState<DetailTabKey>(data.defaultTab);
  const [messages, setMessages] = useState(data.messages);
  const [sending, setSending] = useState(false);
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
  const currentTab = useMemo(() => data.outputTabs.find((tab) => tab.key === activeTab) ?? data.outputTabs[0], [activeTab, data.outputTabs]);
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
  const selectedTone =
    currentTab.accent === "chat"
      ? "border-emerald-200 bg-emerald-50 text-emerald-600"
      : currentTab.accent === "doc"
        ? "border-blue-300 bg-blue-50 text-blue-600 shadow-[0_8px_18px_rgba(59,130,246,0.08)]"
        : "border-violet-200 bg-violet-50 text-violet-600";
  const dropdownLabel = isCanvasMode ? "画布 / Canvas" : "文稿 / Markdown";
  const conversationTone = isCanvasMode ? "canvas" : "doc";
  const searchNeedle = workspaceSearchQuery.trim().toLowerCase();
  const filteredMessages = useMemo(() => {
    if (!searchNeedle) return messages;
    return messages.filter((m) => {
      const blob = [m.author, m.body, m.time, m.helperText].filter(Boolean).join(" ").toLowerCase();
      return blob.includes(searchNeedle);
    });
  }, [messages, searchNeedle]);
  const filteredContextSources = useMemo(() => {
    if (!searchNeedle) return data.contextSources;
    return data.contextSources.filter((item) => {
      const blob = [item.title, item.description].join(" ").toLowerCase();
      return blob.includes(searchNeedle);
    });
  }, [data.contextSources, searchNeedle]);
  const topRowNodes = canvasNodes.slice(0, 3);
  const bottomRowNodes = canvasNodes.slice(3, 6);

  useEffect(() => {
    if (!canvasNotice) return;
    const timer = window.setTimeout(() => setCanvasNotice(null), 2400);
    return () => window.clearTimeout(timer);
  }, [canvasNotice]);

  useEkoSessionRealtime({ sessionId: data.id });

  const agentSlice = useAgentRuntimeStore((s) => s.sessions[data.id]);
  const phase = agentSlice?.phase ?? "IDLE";
  const wsStatus = agentSlice?.wsStatus ?? "idle";
  const useMockFb = agentSlice?.useMockFallback ?? false;
  const docStream = agentSlice?.docMarkdownStream ?? "";
  const docConflict = agentSlice?.documentConflict ?? false;
  const lastErr = agentSlice?.lastError ?? null;

  const mergedWorkflow = useMemo(
    () => mergeWorkflowSteps(data.workflow, agentSlice?.planningSteps ?? []),
    [data.workflow, agentSlice?.planningSteps],
  );

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
      const now = new Date();
      const hh = now.getHours().toString().padStart(2, "0");
      const mm = now.getMinutes().toString().padStart(2, "0");
      const time = `${hh}:${mm}`;
      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          author: "我",
          role: "member" as const,
          time,
          body: text,
          avatar: "我",
          sent: true,
        },
      ]);

      const store = useAgentRuntimeStore.getState();
      store.patchSession(data.id, { phase: "ANALYZING", lastError: null });

      setSending(true);
      let firstChunk = true;
      const append = (chunk: string) => {
        if (firstChunk) {
          firstChunk = false;
          setActiveTab("doc");
        }
        store.appendDocMarkdown(data.id, chunk);
      };

      try {
        const tried = await streamAgentExecute(
          { session_id: data.id, query: text, stream: true },
          {
            onChunk: append,
            onDone: () => store.ingestEnvelope(data.id, { type: "TASK_COMPLETED", session_id: data.id, payload: {} }),
            onError: () => {},
          },
        );

        if (!tried) {
          await streamDocumentGeneration(
            {
              session_id: data.id,
              topic: data.title,
              requirement: text,
              document_type: "general",
              tone: "formal",
              chat_history: [],
              knowledge_docs: [],
              bitable_records: [],
            },
            {
              onChunk: append,
              onDone: () => store.ingestEnvelope(data.id, { type: "TASK_COMPLETED", session_id: data.id, payload: {} }),
              onError: (msg) => store.patchSession(data.id, { phase: "ERROR", lastError: msg }),
            },
          );
        }

        const doneNow = new Date();
        const dhh = doneNow.getHours().toString().padStart(2, "0");
        const dmm = doneNow.getMinutes().toString().padStart(2, "0");
        setMessages((prev) => [
          ...prev,
          {
            id: `eko-${Date.now()}`,
            author: "Eko",
            role: "eko" as const,
            time: `${dhh}:${dmm}`,
            body: "已收到指令并完成一轮生成；请在「文稿」查看 Markdown 流式输出（若后端未启用 Agent 路由则走文档生成 SSE）。",
            avatar: "E",
            sent: true,
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [data.id, data.title],
  );

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

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden overflow-x-hidden bg-[#FAFBFC] text-slate-900">
      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-5 pb-5 pt-2 sm:px-6 sm:pb-6 sm:pt-3">
            <div className="flex h-full min-h-0 min-w-0 gap-4 overflow-hidden lg:gap-5">
              <div
                className={[
                  "min-h-0 overflow-hidden transition-[width,opacity,transform] duration-300 ease-out",
                  conversationOpen ? "w-[280px] opacity-100" : "pointer-events-none w-0 -translate-x-4 opacity-0",
                ].join(" ")}
              >
                <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-[28px] border border-slate-200/90 bg-white px-5 py-4 shadow-[0_14px_32px_rgba(148,163,184,0.08)]">
                  <div className="flex items-center justify-between">
                    <h2 className="text-[17px] font-semibold text-slate-950">{data.conversationTitle}</h2>
                    <div className="flex items-center gap-1.5">
                      <button type="button" className="rounded-full border border-transparent p-1.5 hover:bg-slate-50">
                        <SmallIcon type="filter" tone="slate" />
                      </button>
                      <button type="button" className="rounded-full border border-transparent p-1.5 hover:bg-slate-50">
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

              <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden sm:gap-3">
                    <section
                      className={`flex min-h-[220px] max-h-[min(42vh,320px)] min-w-0 shrink-0 flex-col overflow-hidden ${detailDesignTokens.card.pageFrame} px-4 py-3`}
                    >
                      <div className="flex min-w-0 flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
                        <div className="min-w-0 flex-1">
                          <h1 className="text-[17px] font-semibold leading-snug tracking-tight text-slate-950 break-words">{data.title}</h1>
                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                            <HeaderBadge tone="neutral">飞书</HeaderBadge>
                            <HeaderBadge tone={isCanvasMode ? "neutral" : "info"}>{isCanvasMode ? "画布" : "文稿"}</HeaderBadge>
                            <HeaderBadge tone={isCanvasMode ? "info" : "success"}>{isCanvasMode ? "进行中" : "已同步"}</HeaderBadge>
                          </div>
                        </div>
                        <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
                          <button
                            type="button"
                            className="inline-flex h-9 items-center gap-1.5 rounded-[12px] border border-slate-200 bg-white px-3 text-[13px] font-semibold text-slate-700 shadow-[0_4px_12px_rgba(15,23,42,0.04)]"
                          >
                            <SmallIcon type="share" tone="slate" />
                            分享
                          </button>
                          <button
                            type="button"
                            className="inline-flex h-9 items-center gap-1.5 rounded-[12px] border border-slate-200 bg-white px-3 text-[13px] font-semibold text-slate-700 shadow-[0_4px_12px_rgba(15,23,42,0.04)]"
                          >
                            <SmallIcon type="download" tone="slate" />
                            导出
                          </button>
                          {!isCanvasMode ? (
                            <button
                              type="button"
                              className="inline-flex h-9 items-center gap-1.5 rounded-[12px] bg-blue-600 px-3 text-[13px] font-semibold text-white shadow-[0_10px_20px_rgba(37,99,235,0.2)]"
                            >
                              <SmallIcon type="sync" tone="blue" />
                              同步
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.04)]"
                          >
                            <MoreIcon />
                          </button>
                        </div>
                      </div>

                      {!isCanvasMode ? (
                        <div
                          className={`mt-2 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden ${detailDesignTokens.card.content} px-3 py-2`}
                        >
                          <h3 className="shrink-0 text-[13px] font-semibold text-slate-950">Agent Mission Control</h3>
                          <AgentRealtimeRibbon phase={phase} wsStatus={wsStatus} useMockFallback={useMockFb} />
                          {lastErr ? (
                            <p className="mb-1 shrink-0 text-[11px] font-medium text-rose-600">生成失败：{lastErr}</p>
                          ) : null}
                          <div className="mt-1 min-h-0 flex-1 overflow-x-auto overflow-y-hidden pb-0.5">
                            <Stepper steps={mergedWorkflow} className="mt-0" />
                          </div>
                          <StepperStatusLegend />
                        </div>
                      ) : (
                        <div className="mt-2 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[18px] border border-slate-200 bg-white px-3 py-2 shadow-[0_8px_20px_rgba(15,23,42,0.04)]">
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">智能体任务控制</p>
                                <span className="inline-flex rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-600">
                                  画布
                                </span>
                              </div>
                              <h2 className="mt-1 text-[14px] font-semibold leading-snug tracking-tight text-slate-950 break-words">{data.missionTitle}</h2>
                              <p className="mt-1 max-w-[520px] text-[10px] leading-relaxed text-slate-500">{data.missionSubtitle}</p>
                            </div>
                            <div className="flex shrink-0 items-end gap-1.5">
                              <div className="flex h-[56px] w-[72px] flex-col justify-between overflow-hidden rounded-[10px] border border-slate-200 bg-white px-2 py-1.5 shadow-[0_4px_12px_rgba(15,23,42,0.03)]">
                                <p className="truncate text-[10px] leading-4 text-slate-400">置信度</p>
                                <p className="truncate text-[16px] leading-none font-semibold tracking-tight tabular-nums text-violet-600">{data.confidence}</p>
                              </div>
                              <div className="flex h-[56px] w-[72px] flex-col justify-between overflow-hidden rounded-[10px] border border-slate-200 bg-white px-2 py-1.5 shadow-[0_4px_12px_rgba(15,23,42,0.03)]">
                                <p className="truncate text-[10px] leading-4 text-slate-400">上下文质量</p>
                                <p className="truncate text-[16px] leading-none font-semibold tracking-tight tabular-nums text-amber-600">{data.contextQuality}</p>
                              </div>
                            </div>
                          </div>
                          <AgentRealtimeRibbon phase={phase} wsStatus={wsStatus} useMockFallback={useMockFb} />
                          <div className="mt-1 min-h-0 flex-1 overflow-x-auto overflow-y-hidden pb-0.5">
                            <Stepper steps={mergedWorkflow} className="mt-0" />
                          </div>
                          <StepperStatusLegend />
                        </div>
                      )}
                    </section>

                    <section className={`min-h-0 flex flex-1 flex-col overflow-hidden ${detailDesignTokens.card.panel} ${detailDesignTokens.spacing.panelPadding}`}>
                      <div className="flex min-w-0 items-center justify-between gap-4 overflow-hidden">
                        <p className="shrink-0 text-[17px] font-semibold text-slate-950">输出内容</p>
                        <button className="inline-flex h-10 shrink-0 items-center rounded-[14px] border border-slate-200 bg-white px-4 text-[14px] font-medium text-slate-600 shadow-[0_4px_12px_rgba(15,23,42,0.04)]">
                          {dropdownLabel}
                        </button>
                      </div>
                      <div className="mt-2.5 flex min-w-0 flex-wrap gap-2 overflow-hidden">
                        {data.outputTabs.map((tab) => (
                          <button
                            key={tab.key}
                            type="button"
                            onClick={() => setActiveTab(tab.key)}
                            className={[
                              "inline-flex h-[48px] min-w-[118px] max-w-[148px] min-w-0 items-center gap-2 overflow-hidden rounded-[16px] border px-3 text-left transition",
                              activeTab === tab.key ? selectedTone : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50",
                            ].join(" ")}
                          >
                            <div className="flex h-[32px] w-[32px] shrink-0 items-center justify-center rounded-[11px] border border-current/10 bg-white/80">
                              <SmallIcon type={tab.key === "chat" ? "chat" : tab.key === "doc" ? "doc" : "deck"} tone={tab.key === "chat" ? "green" : tab.key === "doc" ? "blue" : "purple"} />
                            </div>
                            <div>
                              <p className="truncate text-[13px] font-semibold">{tab.label}</p>
                              <p className="line-clamp-1 text-[10px] leading-[14px] text-slate-400">
                                {tab.key === "chat" ? "显示即时回复" : tab.key === "doc" ? "显示结构化文稿" : "显示可视化汇报结构"}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>

                      <div className="mt-2.5 min-h-0 flex-1 overflow-hidden rounded-[22px] border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.03)]">
                        <AnimatePresence mode="wait">
                          {activeTab === "doc" ? (
                            <motion.div key="doc-tab" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }} className="flex h-full min-h-0 flex-col">
                            <div className="shrink-0 border-b border-slate-100 px-5 py-3">
                              <h3 className="truncate text-[16px] font-semibold text-slate-950">{data.document.title}</h3>
                              <p className="mt-1 text-[12px] text-slate-500">{data.document.date}</p>
                              {docConflict ? (
                                <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-900">
                                  检测到服务端文稿版本与本地草稿可能冲突，请以服务端为准或稍后刷新。
                                </p>
                              ) : null}
                            </div>
                            <div className="min-h-0 flex-1 overflow-y-auto px-[18px] py-3 pr-3">
                              <div className="space-y-[14px] pb-8">
                                {docStream ? (
                                  <motion.section
                                    layout
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="rounded-[18px] border border-blue-200/80 bg-blue-50/40 px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]"
                                  >
                                    <div className="flex items-center justify-between gap-2">
                                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-600">
                                        Word 预览 · 流式 Markdown
                                      </p>
                                      {agentSlice?.isDocStreaming ? (
                                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-600">
                                          <motion.span
                                            className="inline-block h-1.5 w-1.5 rounded-full bg-blue-500"
                                            animate={{ opacity: [0.4, 1, 0.4] }}
                                            transition={{ repeat: Infinity, duration: 1 }}
                                          />
                                          写入中
                                        </span>
                                      ) : (
                                        <span className="text-[11px] text-slate-500">已完成本段</span>
                                      )}
                                    </div>
                                    <div className="prose prose-sm mt-3 max-w-none text-slate-800 prose-headings:my-2 prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0.5">
                                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{docStream}</ReactMarkdown>
                                    </div>
                                  </motion.section>
                                ) : null}
                                {data.document.sections.map((section, secIdx) => (
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
                                ))}
                              </div>
                            </div>
                            </motion.div>
                          ) : activeTab === "chat" ? (
                            <motion.div key="chat-tab" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }} className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.03)]">
                            <h4 className="text-[17px] font-semibold text-slate-950">{data.chatReply.title}</h4>
                            <p className="mt-3 text-[15px] leading-8 text-slate-700">{data.chatReply.body}</p>
                            <p className="mt-5 text-[13px] text-slate-400">{data.chatReply.source}</p>
                            </motion.div>
                          ) : (
                            <motion.div key="canvas-tab" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }} className="min-h-0 h-full overflow-y-auto px-3 pb-3 pt-1">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Output Surface</p>
                                <h3 className="mt-0.5 text-[15px] font-semibold text-slate-950">Canvas Preview</h3>
                                <p className="mt-0.5 line-clamp-1 text-[11px] text-slate-500">A PPT-like visual surface for storyline arrangement, ready to evolve.</p>
                              </div>
                              <div className="flex shrink-0 items-center gap-2">
                                <Link
                                  href={`/canvas?session=${encodeURIComponent(data.id)}`}
                                  prefetch={false}
                                  className="inline-flex h-8 items-center gap-1.5 rounded-[10px] border border-violet-200 bg-violet-50 px-2.5 text-[12px] font-semibold text-violet-600 shadow-[0_6px_16px_rgba(139,92,246,0.08)] transition hover:bg-violet-100"
                                >
                                  打开 Tldraw 画布
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
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </section>
              </div>

              <aside className="min-h-0 w-[300px] shrink-0 space-y-3 overflow-y-auto pr-1 lg:w-[320px]">
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
                                  const srcIndex = data.contextSources.findIndex((s) => s.id === item.id);
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
                                {data.sourceEvidence.map((item) => (
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
                              const srcIndex = data.contextSources.findIndex((s) => s.id === item.id);
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
                              <button className="mt-3 text-[13px] font-semibold text-blue-600">{data.memoryNote?.action}</button>
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
