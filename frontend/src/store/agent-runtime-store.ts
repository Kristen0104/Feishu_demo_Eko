import { create } from "zustand";

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

type SessionAgentSlice = {
  phase: AgentPhase;
  intent: AgentIntent;
  progress: number;
  planningPlan: PlanningPlanWire | null;
  planningSteps: PlanningStepWire[];
  retrievedSources: RetrievedSourceWire[];
  docMarkdownStream: string;
  isDocStreaming: boolean;
  documentVersion: number;
  canvasVersion: number;
  wsStatus: "idle" | "connecting" | "open" | "closed" | "error";
  useMockFallback: boolean;
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
  docMarkdownStream: "",
  isDocStreaming: false,
  documentVersion: 0,
  canvasVersion: 0,
  wsStatus: "idle",
  useMockFallback: false,
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

export const useAgentRuntimeStore = create<AgentRuntimeStore>((set, get) => ({
  sessions: {},

  ensureSession: (sessionId) =>
    set((state) => {
      if (state.sessions[sessionId]) return state;
      return { sessions: { ...state.sessions, [sessionId]: defaultSlice() } };
    }),

  resetSession: (sessionId) =>
    set((state) => ({
      sessions: { ...state.sessions, [sessionId]: defaultSlice() },
    })),

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

      if (eventName === "retrieval.completed") {
        get().patchSession(sid, {
          phase: "RETRIEVING",
          retrievedSources: parseRetrievedSources(payload),
        });
        return;
      }

      if (eventName === "plan.created") {
        const planPayload = payload.plan && typeof payload.plan === "object" ? (payload.plan as Record<string, unknown>) : payload;
        const planningPlan = parsePlanningPayload(planPayload);
        get().patchSession(sid, {
          phase: "RETRIEVING",
          planningPlan,
          planningSteps: planningPlan?.steps ?? [],
        });
        return;
      }

      if (eventName === "plan.step") {
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

      if (eventName === "tool.selected" || eventName === "tool.started" || eventName === "tool.completed") {
        get().patchSession(sid, { phase: "GENERATING" });
        return;
      }

      if (eventName === "result.created") {
        const response = payload.response && typeof payload.response === "object" ? (payload.response as Record<string, unknown>) : {};
        const artifact = response.artifact && typeof response.artifact === "object" ? (response.artifact as Record<string, unknown>) : null;
        const content = artifact && typeof artifact.content === "string" ? artifact.content : "";
        const append = payload.append === true;
        if (content && append) {
          get().patchSession(sid, { phase: "GENERATING", isDocStreaming: true });
          get().appendDocMarkdown(sid, content);
          return;
        }
        get().patchSession(sid, {
          phase: response.status === "failed" ? "ERROR" : "COMPLETED",
          progress: 1,
          isDocStreaming: false,
          ...(content ? { docMarkdownStream: content } : {}),
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
      case "TASK_COMPLETED":
        if (payload.status === "进行中" || payload.status === "running" || payload.status === "queued") {
          get().patchSession(sid, {
            phase: "GENERATING",
            progress: typeof payload.progress === "number" ? payload.progress : slice.progress,
          });
          break;
        }
        const artifact = payload.artifact as Record<string, unknown> | undefined;
        const artifactContent = artifact && typeof artifact.content === "string" ? artifact.content : "";
        get().patchSession(sid, {
          phase: "COMPLETED",
          progress: 1,
          isDocStreaming: false,
          ...(artifactContent ? { docMarkdownStream: artifactContent } : {}),
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
