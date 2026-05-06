export const COLLAB_EVENTS = {
  MANUAL_UPDATE: "MANUAL_UPDATE",
  AI_COMMAND: "AI_COMMAND",
  CANVAS_SYNC: "CANVAS_SYNC",
  STATUS_BUSY: "STATUS_BUSY",
  STATUS_IDLE: "STATUS_IDLE",
  SESSION_META: "SESSION_META",
} as const;

export type CollabEventName = (typeof COLLAB_EVENTS)[keyof typeof COLLAB_EVENTS];

export type CollabStatus = "idle" | "ai_generating";

export type CollabSessionPayload = {
  owner_id?: string;
  status?: CollabStatus;
  progress?: number;
  canvas_data?: Record<string, unknown>;
  sources?: string[];
};

export type CollabEnvelope = {
  event: CollabEventName;
  payload?: CollabSessionPayload;
};

export const COLLAB_API_PATHS = {
  FEISHU_SAVE: "/api/v1/feishu/save",
} as const;
