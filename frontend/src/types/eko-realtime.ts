export type AgentPhase =
  | "IDLE"
  | "ANALYZING"
  | "RETRIEVING"
  | "GENERATING"
  | "SYNCING"
  | "COMPLETED"
  | "ERROR";

/** Aligns with MULTI_DEVICE_SYNC_SPEC + backend-style envelopes. */
export type RealtimeEnvelope =
  | {
      type:
        | "SESSION_CONNECTED"
        | "SESSION_OPENED"
        | "INTENT_RECOGNIZED"
        | "CANVAS_UPDATE"
        | "TASK_COMPLETED"
        | "CURSOR_SYNC"
        | "ERROR";
      payload?: Record<string, unknown>;
      session_id?: string;
    }
  | {
      type: "agent.state.changed";
      sessionId: string;
      state: AgentPhase;
      progress?: number;
    }
  | {
      type: "document.updated";
      sessionId: string;
      markdown: string;
      version: number;
    };
