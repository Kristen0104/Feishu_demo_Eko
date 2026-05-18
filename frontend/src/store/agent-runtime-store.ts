import { create } from "zustand";

import type { AgentChatStreamEvent } from "@/lib/agent/sse-stream";
import type { AgentPhase } from "@/types/eko-realtime";
import type { WorkflowStatus } from "@/types/workspace";

export type { AgentPhase };

export type AgentIntent = "CHAT" | "DOC" | "PPT" | "CANVAS" | null;

export type PlanningStepWire = {
  id: string;
  title: string;
  description?: string;
  type?: string;
  tool?: string;
  input?: Record<string, unknown>;
  expectedOutput?: string;
  dependsOn?: string[];
  status: WorkflowStatus;
};

export type PlanningPlanWire = {
  goal: string;
  intent: string;
  taskComplexity: "simple" | "medium" | "complex" | string;
  missingInfo: string[];
  needClarification: boolean;
  questions: string[];
  assumptions: string[];
  clarificationNeeded?: boolean;
  clarificationQuestion?: string | null;
  summary: string;
  steps: PlanningStepWire[];
  finalOutput?: {
    format: string;
    requirements: string[];
  };
};

export type RetrievedSourceWire = {
  sourceId: string;
  sourceType: string;
  title: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
};

export type ContextMessageWire = {
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

type SessionAgentSlice = {
  phase: AgentPhase;
  intent: AgentIntent;
  progress: number;
  planningPlan: PlanningPlanWire | null;
  planningSteps: PlanningStepWire[];
  retrievedSources: RetrievedSourceWire[];
  contextMessages: ContextMessageWire[];
  docMarkdownStream: string;
  isDocStreaming: boolean;
  documentVersion: number;
  canvasVersion: number;
  wsStatus: "idle" | "connecting" | "open" | "closed" | "error";
  lastServerDocumentVersion: number;
  documentConflict: boolean;
  lastError: string | null;
};

const defaultSlice = (): SessionAgentSlice => ({
  phase: "IDLE",
  intent: null,
  progress: 0,
  planningPlan: null,
  planningSteps: [],
  retrievedSources: [],
  contextMessages: [],
  docMarkdownStream: "",
  isDocStreaming: false,
  documentVersion: 0,
  canvasVersion: 0,
  wsStatus: "idle",
  lastServerDocumentVersion: 0,
  documentConflict: false,
  lastError: null,
});

type AgentRuntimeStore = {
  sessions: Record<string, SessionAgentSlice>;
  ensureSession: (sessionId: string) => void;
  resetSession: (sessionId: string) => void;
  patchSession: (sessionId: string, patch: Partial<SessionAgentSlice>) => void;
  setPhase: (sessionId: string, phase: AgentPhase) => void;
  appendDocMarkdown: (sessionId: string, chunk: string) => void;
  replaceDocMarkdown: (sessionId: string, markdown: string, version: number) => void;
  ingestEnvelope: (sessionId: string, raw: unknown) => void;
};

const DOCUMENT_STREAM_FLUSH_MS = 34;
const pendingDocumentStreams = new Map<
  string,
  {
    payload: Record<string, unknown>;
    timer: ReturnType<typeof setTimeout>;
  }
>();

function coerceWorkflowStatus(s: string | undefined): WorkflowStatus {
  if (s === "completed" || s === "running" || s === "pending" || s === "warning") return s;
  return "pending";
}

function parsePlanningPayload(payload: Record<string, unknown>): PlanningPlanWire | null {
  const steps = payload.steps;
  const parsedSteps = Array.isArray(steps)
    ? steps.map((step, index) => {
    if (step && typeof step === "object" && "title" in step) {
      const o = step as {
        id?: string;
        step_id?: string;
        title?: string;
        name?: string;
        description?: string;
        type?: string;
        tool?: string | null;
        input?: Record<string, unknown>;
        inputs?: Record<string, unknown>;
        expected_output?: string;
        expectedOutput?: string;
        depends_on?: string[];
        dependsOn?: string[];
        status?: string;
      };
      const title = typeof o.title === "string" ? o.title : typeof o.name === "string" ? o.name : `步骤 ${index + 1}`;
      const id = typeof o.id === "string" ? o.id : typeof o.step_id === "string" ? o.step_id : String(index + 1);
      return {
        id,
        title,
        description: typeof o.description === "string" ? o.description : undefined,
        type: typeof o.type === "string" ? o.type : undefined,
        tool: typeof o.tool === "string" ? o.tool : undefined,
        input: o.input ?? o.inputs,
        expectedOutput:
          typeof o.expected_output === "string"
            ? o.expected_output
            : typeof o.expectedOutput === "string"
              ? o.expectedOutput
              : undefined,
        dependsOn: Array.isArray(o.depends_on) ? o.depends_on : Array.isArray(o.dependsOn) ? o.dependsOn : [],
        status: coerceWorkflowStatus(o.status),
      };
    }
    return {
      id: String(index + 1),
      title: String(step),
      status: "pending" as const,
    };
  })
    : [];
  const finalOutput = payload.final_output;
  const hasSummary = typeof payload.goal === "string" || typeof payload.summary === "string";
  const hasClarification =
    Array.isArray(payload.missing_info) ||
    Array.isArray(payload.questions) ||
    typeof payload.clarification_question === "string";
  const hasFinalOutput = finalOutput && typeof finalOutput === "object";
  if (!parsedSteps.length && !hasSummary && !hasClarification && !hasFinalOutput) return null;
  return {
    goal: typeof payload.goal === "string" ? payload.goal : "",
    intent: typeof payload.intent === "string" ? payload.intent : "",
    taskComplexity: typeof payload.task_complexity === "string" ? payload.task_complexity : "medium",
    missingInfo: Array.isArray(payload.missing_info) ? payload.missing_info.filter((item): item is string => typeof item === "string") : [],
    needClarification: Boolean(payload.need_clarification),
    questions: Array.isArray(payload.questions) ? payload.questions.filter((item): item is string => typeof item === "string") : [],
    assumptions: Array.isArray(payload.assumptions) ? payload.assumptions.filter((item): item is string => typeof item === "string") : [],
    clarificationNeeded: Boolean(payload.clarification_needed),
    clarificationQuestion: typeof payload.clarification_question === "string" ? payload.clarification_question : null,
    summary: typeof payload.summary === "string" ? payload.summary : "",
    steps: parsedSteps,
    finalOutput:
      finalOutput && typeof finalOutput === "object"
        ? {
            format: typeof (finalOutput as { format?: unknown }).format === "string" ? (finalOutput as { format: string }).format : "",
            requirements: Array.isArray((finalOutput as { requirements?: unknown }).requirements)
              ? ((finalOutput as { requirements: unknown[] }).requirements.filter((item): item is string => typeof item === "string"))
              : [],
          }
        : undefined,
  };
}

function parseRetrievedSources(payload: Record<string, unknown>): RetrievedSourceWire[] {
  const sources = payload.sources;
  if (!Array.isArray(sources)) return [];
  return sources
    .map((source, index): RetrievedSourceWire | null => {
      if (!source || typeof source !== "object") return null;
      const o = source as Record<string, unknown>;
      const sourceId = typeof o.source_id === "string" ? o.source_id : typeof o.sourceId === "string" ? o.sourceId : `source_${index + 1}`;
      const sourceType = typeof o.source_type === "string" ? o.source_type : typeof o.sourceType === "string" ? o.sourceType : "knowledge_doc";
      return {
        sourceId,
        sourceType,
        title: typeof o.title === "string" && o.title.trim() ? o.title : "RAG 命中资料",
        content: typeof o.content === "string" ? o.content : "",
        score: typeof o.score === "number" ? o.score : 0,
        metadata: o.metadata && typeof o.metadata === "object" ? (o.metadata as Record<string, unknown>) : {},
      };
    })
    .filter((source): source is RetrievedSourceWire => source !== null);
}

function inferAgentEventChannel(event: Pick<AgentChatStreamEvent, "event" | "channel">): NonNullable<AgentChatStreamEvent["channel"]> {
  if (event.channel) return event.channel;
  switch (event.event) {
    case "turn.started":
    case "intent.recognized":
    case "retrieval.started":
    case "tool.started":
      return "status";
    case "context.loaded":
    case "retrieval.completed":
    case "source.bitable.started":
    case "source.bitable.completed":
    case "source.bitable.empty":
    case "source.bitable.failed":
      return "sources";
    case "plan.created":
    case "plan.summary":
    case "plan.step":
      return "plan";
    case "result.created":
      return "chat";
    case "artifact.archived":
    case "artifact.archive_failed":
    case "artifact.delta":
      return "artifact";
    case "clarification.requested":
      return "chat";
    case "turn.failed":
      return "error";
    case "tool.selected":
    case "tool.completed":
    default:
      return "log";
  }
}

function streamDocumentPatch(payload: Record<string, unknown>, current: SessionAgentSlice): Partial<SessionAgentSlice> | null {
  const artifact = payload.artifact && typeof payload.artifact === "object" ? (payload.artifact as Record<string, unknown>) : {};
  const content = typeof payload.content === "string" ? payload.content : typeof artifact.content === "string" ? artifact.content : "";
  const chunk = typeof payload.chunk === "string" ? payload.chunk : "";
  const nextContent = content || (chunk ? `${current.docMarkdownStream}${chunk}` : "");
  if (!nextContent) return null;

  const currentContent = current.docMarkdownStream;
  if (current.phase === "COMPLETED" || current.phase === "ERROR") return null;
  if (nextContent === currentContent && current.isDocStreaming) return null;
  if (current.isDocStreaming && currentContent.length > nextContent.length && currentContent.startsWith(nextContent)) return null;

  return {
    intent: "DOC",
    phase: "GENERATING",
    docMarkdownStream: nextContent,
    isDocStreaming: true,
    lastError: null,
  };
}

function resolveFinalDocumentContent(incoming: string, current: string): string {
  if (!incoming) return current;
  if (current.length > incoming.length && current.startsWith(incoming)) return current;
  return incoming;
}

function flushPendingDocumentStream(sessionId: string, get: () => AgentRuntimeStore): void {
  const queued = pendingDocumentStreams.get(sessionId);
  if (!queued) return;
  clearTimeout(queued.timer);
  pendingDocumentStreams.delete(sessionId);
  const current = get().sessions[sessionId] ?? defaultSlice();
  const patch = streamDocumentPatch(queued.payload, current);
  if (patch) {
    get().patchSession(sessionId, patch);
  }
}

function scheduleDocumentStreamPatch(sessionId: string, payload: Record<string, unknown>, get: () => AgentRuntimeStore): void {
  const latest = get().sessions[sessionId] ?? defaultSlice();
  if (latest.phase === "COMPLETED" || latest.phase === "ERROR") return;

  const pending = pendingDocumentStreams.get(sessionId);
  if (pending) {
    pending.payload = payload;
    return;
  }

  const timer = setTimeout(() => {
    flushPendingDocumentStream(sessionId, get);
  }, DOCUMENT_STREAM_FLUSH_MS);
  pendingDocumentStreams.set(sessionId, { payload, timer });
}

function parseContextMessages(value: unknown): ContextMessageWire[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      role: typeof item.role === "string" && item.role ? item.role : "user",
      content: typeof item.content === "string" ? item.content : "",
      timestamp: typeof item.timestamp === "number" ? item.timestamp : null,
      sender_open_id: typeof item.sender_open_id === "string" ? item.sender_open_id : null,
      sender_union_id: typeof item.sender_union_id === "string" ? item.sender_union_id : null,
      sender_name: typeof item.sender_name === "string" ? item.sender_name : null,
      platform_user_id: typeof item.platform_user_id === "string" ? item.platform_user_id : null,
      platform_display_name: typeof item.platform_display_name === "string" ? item.platform_display_name : null,
      avatar_url: typeof item.avatar_url === "string" ? item.avatar_url : null,
    }))
    .filter((item) => item.content.trim().length > 0);
}

export const useAgentRuntimeStore = create<AgentRuntimeStore>((set, get) => ({
  sessions: {},

  ensureSession: (sessionId) =>
    set((state) => {
      if (state.sessions[sessionId]) return state;
      return { sessions: { ...state.sessions, [sessionId]: defaultSlice() } };
    }),

  resetSession: (sessionId) =>
    set((state) => {
      const pending = pendingDocumentStreams.get(sessionId);
      if (pending) {
        clearTimeout(pending.timer);
        pendingDocumentStreams.delete(sessionId);
      }
      return {
        sessions: { ...state.sessions, [sessionId]: defaultSlice() },
      };
    }),

  patchSession: (sessionId, patch) =>
    set((state) => {
      const prev = state.sessions[sessionId] ?? defaultSlice();
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: { ...prev, ...patch },
        },
      };
    }),

  setPhase: (sessionId, phase) =>
    set((state) => {
      const prev = state.sessions[sessionId] ?? defaultSlice();
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: { ...prev, phase },
        },
      };
    }),

  appendDocMarkdown: (sessionId, chunk) =>
    set((state) => {
      const prev = state.sessions[sessionId] ?? defaultSlice();
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...prev,
            docMarkdownStream: prev.docMarkdownStream + chunk,
            isDocStreaming: true,
          },
        },
      };
    }),

  replaceDocMarkdown: (sessionId, markdown, version) =>
    set((state) => {
      const prev = state.sessions[sessionId] ?? defaultSlice();
      const conflict =
        prev.documentVersion > prev.lastServerDocumentVersion &&
        version < prev.documentVersion &&
        markdown !== prev.docMarkdownStream;

      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...prev,
            docMarkdownStream: markdown,
            lastServerDocumentVersion: Math.max(prev.lastServerDocumentVersion, version),
            documentVersion: Math.max(prev.documentVersion, version),
            documentConflict: conflict || prev.documentConflict,
            isDocStreaming: false,
          },
        },
      };
    }),

  ingestEnvelope: (sessionId, raw) => {
    const slice = get().sessions[sessionId] ?? defaultSlice();
    if (!raw || typeof raw !== "object") return;

    const body = raw as Record<string, unknown>;
    const eventName = typeof body.event === "string" ? body.event : "";
    if (eventName) {
      const channel = inferAgentEventChannel({
        event: eventName as AgentChatStreamEvent["event"],
        channel: typeof body.channel === "string" ? (body.channel as AgentChatStreamEvent["channel"]) : undefined,
      });
      const payload = (body.payload ?? {}) as Record<string, unknown>;
      const sid = typeof payload.session_id === "string" ? payload.session_id : sessionId;

      if (eventName === "turn.started" || eventName === "intent.recognized") {
        const intentRaw = payload.intent;
        get().patchSession(sid, {
          phase: "ANALYZING",
          intent:
            intentRaw === "chat"
              ? "CHAT"
              : intentRaw === "docx"
                ? "DOC"
                : intentRaw === "ppt"
                  ? "PPT"
                  : intentRaw === "board"
                    ? "CANVAS"
                    : slice.intent,
        });
        return;
      }

      if (eventName === "retrieval.started") {
        get().patchSession(sid, { phase: "RETRIEVING", retrievedSources: [] });
        return;
      }

      if (eventName === "retrieval.completed" && channel === "sources") {
        get().patchSession(sid, {
          phase: "RETRIEVING",
          retrievedSources: parseRetrievedSources(payload),
        });
        return;
      }

      if (eventName === "source.bitable.completed" && channel === "sources") {
        const bitableSources = parseRetrievedSources({ sources: payload.records });
        get().patchSession(sid, {
          phase: "RETRIEVING",
          retrievedSources: [...slice.retrievedSources.filter((source) => source.sourceType !== "bitable"), ...bitableSources],
        });
        return;
      }

      if (eventName === "source.bitable.failed") {
        get().patchSession(sid, {
          lastError: typeof body.message === "string" ? body.message : "Bitable 查询失败",
        });
        return;
      }

      if (eventName === "plan.created" && channel === "plan") {
        const planPayload = payload.plan && typeof payload.plan === "object" ? (payload.plan as Record<string, unknown>) : payload;
        const planningPlan = parsePlanningPayload(planPayload);
        get().patchSession(sid, {
          phase: "RETRIEVING",
          planningPlan,
          planningSteps: planningPlan?.steps ?? [],
        });
        return;
      }

      if (eventName === "plan.step" && channel === "plan") {
        const stepPayload = payload.step && typeof payload.step === "object" ? (payload.step as Record<string, unknown>) : null;
        if (stepPayload) {
          const parsed = parsePlanningPayload({ steps: [stepPayload] });
          const step = parsed?.steps[0];
          if (step) {
            get().patchSession(sid, {
              phase: "RETRIEVING",
              planningSteps: [...slice.planningSteps.filter((candidate) => candidate.id !== step.id), step],
            });
          }
        }
        return;
      }

      if (eventName === "clarification.requested") {
        const questions = Array.isArray(payload.questions) ? payload.questions.filter((item): item is string => typeof item === "string") : [];
        const planningPlan = parsePlanningPayload({
          goal: "确认用户意图",
          intent: "intent_clarification",
          missing_info: ["intent"],
          need_clarification: true,
          clarification_needed: true,
          clarification_question: typeof body.message === "string" ? body.message : questions[0] ?? "请确认要执行的动作。",
          questions,
          assumptions: [],
          summary: typeof body.message === "string" ? body.message : questions[0] ?? "请确认要执行的动作。",
          steps: [],
          final_output: { format: "clarification", requirements: [] },
        });
        get().patchSession(sid, {
          phase: "ANALYZING",
          planningPlan,
          planningSteps: [],
          isDocStreaming: false,
          lastError: null,
        });
        return;
      }

      if (eventName === "tool.selected" || eventName === "tool.started" || eventName === "tool.completed") {
        get().patchSession(sid, { phase: "GENERATING" });
        return;
      }

      if (eventName === "artifact.delta") {
        scheduleDocumentStreamPatch(sid, payload, get);
        return;
      }

      if (eventName === "result.created") {
        flushPendingDocumentStream(sid, get);
        const latest = get().sessions[sid] ?? slice;
        const response = payload.response && typeof payload.response === "object" ? (payload.response as Record<string, unknown>) : {};
        const artifact = response.artifact && typeof response.artifact === "object" ? (response.artifact as Record<string, unknown>) : null;
        const content = artifact && typeof artifact.content === "string" ? artifact.content : "";
        const append = payload.append === true;
        if (content && append) {
          const fullContent = typeof payload.content === "string" ? payload.content : "";
          get().patchSession(sid, {
            intent: "DOC",
            phase: "GENERATING",
            isDocStreaming: true,
            docMarkdownStream: fullContent || `${slice.docMarkdownStream}${content}`,
            lastError: null,
          });
          return;
        }
        get().patchSession(sid, {
          phase: response.status === "failed" ? "ERROR" : "COMPLETED",
          progress: 1,
          isDocStreaming: false,
          docMarkdownStream: resolveFinalDocumentContent(content, (get().sessions[sid] ?? latest).docMarkdownStream),
        });
        return;
      }

      if (eventName === "turn.failed") {
        get().patchSession(sid, {
          phase: "ERROR",
          lastError: typeof body.message === "string" ? body.message : "Unknown error",
        });
        return;
      }
    }

    const type = typeof body.type === "string" ? body.type : "";

    if (type === "agent.state.changed" && typeof body.sessionId === "string") {
      const st = body.state;
      if (
        st === "IDLE" ||
        st === "ANALYZING" ||
        st === "RETRIEVING" ||
        st === "GENERATING" ||
        st === "SYNCING" ||
        st === "COMPLETED" ||
        st === "ERROR"
      ) {
        get().patchSession(body.sessionId, {
          phase: st,
          progress: typeof body.progress === "number" ? body.progress : slice.progress,
        });
      }
      return;
    }

    if (type === "document.updated" && typeof body.sessionId === "string") {
      const md = typeof body.markdown === "string" ? body.markdown : "";
      const version = typeof body.version === "number" ? body.version : slice.documentVersion + 1;
      get().replaceDocMarkdown(body.sessionId, md, version);
      return;
    }

    const payload = (body.payload ?? body) as Record<string, unknown>;
    const sid = typeof body.session_id === "string" ? body.session_id : sessionId;

    switch (type) {
      case "INTENT_RECOGNIZED": {
        const intentRaw = payload.intent ?? payload.mode;
        const intent =
          intentRaw === "CHAT" || intentRaw === "DOC" || intentRaw === "PPT" || intentRaw === "CANVAS"
            ? intentRaw
            : null;
        get().patchSession(sid, {
          intent,
          phase: "ANALYZING",
        });
        break;
      }
      case "SESSION_OPENED":
        get().patchSession(sid, {
          phase: "ANALYZING",
          lastError: null,
          contextMessages: parseContextMessages(payload.context_messages),
        });
        break;
      case "CONTEXT_LOADED":
        get().patchSession(sid, {
          phase: payload.status === "等待选择" ? "ANALYZING" : slice.phase,
          contextMessages: parseContextMessages(payload.context_messages),
        });
        break;
      case "AGENT_PLANNING":
        const planningPlan = parsePlanningPayload(payload);
        get().patchSession(sid, {
          phase: "RETRIEVING",
          planningPlan,
          planningSteps: planningPlan?.steps ?? [],
        });
        break;
      case "CANVAS_UPDATE":
        get().patchSession(sid, {
          phase: "GENERATING",
          canvasVersion:
            typeof payload.version === "number" ? payload.version : slice.canvasVersion + 1,
        });
        break;
      case "DOC_STREAM": {
        scheduleDocumentStreamPatch(sid, payload, get);
        break;
      }
      case "TASK_COMPLETED":
        if (payload.status === "进行中" || payload.status === "running" || payload.status === "queued") {
          if (slice.phase === "COMPLETED" || slice.phase === "ERROR") break;
          get().patchSession(sid, {
            phase: "GENERATING",
            progress: typeof payload.progress === "number" ? payload.progress : slice.progress,
          });
          break;
        }
        flushPendingDocumentStream(sid, get);
        const artifact = payload.artifact as Record<string, unknown> | undefined;
        const artifactContent = artifact && typeof artifact.content === "string" ? artifact.content : "";
        get().patchSession(sid, {
          phase: "COMPLETED",
          progress: 1,
          isDocStreaming: false,
          docMarkdownStream: resolveFinalDocumentContent(artifactContent, (get().sessions[sid] ?? slice).docMarkdownStream),
        });
        break;
      case "CURSOR_SYNC":
        break;
      case "ERROR":
        get().patchSession(sid, {
          phase: "ERROR",
          lastError: typeof payload.message === "string" ? payload.message : "Unknown error",
        });
        break;
      default:
        break;
    }
  },
}));
