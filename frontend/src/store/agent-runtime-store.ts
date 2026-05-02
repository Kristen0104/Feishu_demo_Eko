import { create } from "zustand";

import type { AgentPhase } from "@/types/eko-realtime";
import type { WorkflowStatus } from "@/types/workspace";

export type { AgentPhase };

export type AgentIntent = "CHAT" | "DOC" | "PPT" | "CANVAS" | null;

export type PlanningStepWire = {
  id: string;
  title: string;
  status: WorkflowStatus;
};

type SessionAgentSlice = {
  phase: AgentPhase;
  intent: AgentIntent;
  progress: number;
  planningSteps: PlanningStepWire[];
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
  planningSteps: [],
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

function parsePlanningPayload(payload: Record<string, unknown>): PlanningStepWire[] {
  const steps = payload.steps;
  if (!Array.isArray(steps)) return [];
  return steps.map((step, index) => {
    if (step && typeof step === "object" && "title" in step) {
      const o = step as { id?: string; title?: string; name?: string; status?: string };
      const title = typeof o.title === "string" ? o.title : typeof o.name === "string" ? o.name : `步骤 ${index + 1}`;
      const id = typeof o.id === "string" ? o.id : String(index + 1);
      return {
        id,
        title,
        status: coerceWorkflowStatus(o.status),
      };
    }
    return {
      id: String(index + 1),
      title: String(step),
      status: "pending" as const,
    };
  });
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
      case "AGENT_PLANNING":
        get().patchSession(sid, {
          phase: "RETRIEVING",
          planningSteps: parsePlanningPayload(payload),
        });
        break;
      case "DOC_STREAM": {
        const chunk =
          typeof payload.chunk === "string"
            ? payload.chunk
            : typeof payload.text === "string"
              ? payload.text
              : typeof payload.markdown === "string"
                ? payload.markdown
                : "";
        if (chunk) {
          get().patchSession(sid, { phase: "GENERATING", isDocStreaming: true });
          get().appendDocMarkdown(sid, chunk);
        }
        break;
      }
      case "CANVAS_UPDATE":
        get().patchSession(sid, {
          phase: "GENERATING",
          canvasVersion:
            typeof payload.version === "number" ? payload.version : slice.canvasVersion + 1,
        });
        break;
      case "TASK_COMPLETED":
        get().patchSession(sid, {
          phase: "COMPLETED",
          progress: 1,
          isDocStreaming: false,
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
