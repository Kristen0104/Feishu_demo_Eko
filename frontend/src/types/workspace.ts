export type ScenarioKey = "chat" | "doc" | "canvas";

export type AccentTone = "chat" | "doc" | "canvas";
export type HeaderBadgeTone = "success" | "info" | "neutral";
export type WorkflowStatus = "completed" | "running" | "pending" | "warning";
export type EvidenceTone = "chat" | "document" | "record";

export type HeaderBadge = {
  label: string;
  tone: HeaderBadgeTone;
};

export type MessageItem = {
  id: string;
  author: string;
  role: "member" | "eko";
  time: string;
  body: string;
  mention?: string;
  avatar: string;
};

export type WorkflowStep = {
  id: string;
  title: string;
  status: WorkflowStatus;
};

export type ContextItem = {
  id: string;
  title: string;
  description: string;
  status: WorkflowStatus;
};

export type EvidenceItem = {
  id: string;
  title: string;
  description: string;
  tone: EvidenceTone;
};

export type SyncActionItem = {
  id: string;
  title: string;
  status: WorkflowStatus;
};

export type DocumentSection = {
  title: string;
  body?: string;
  bullets?: string[];
};

export type CanvasNode = {
  id: string;
  index: number;
  title: string;
  bullets: string[];
  icon: "trend" | "rocket" | "calendar" | "spark" | "alert" | "check";
};

export type OutputData =
  | {
      kind: "chat";
      title: string;
      description: string;
      reply: string;
      placeholders: { title: string; subtitle: string }[];
    }
  | {
      kind: "doc";
      title: string;
      description: string;
      badge: string;
      documentTitle: string;
      sections: DocumentSection[];
    }
  | {
      kind: "canvas";
      title: string;
      description: string;
      buttonLabel: string;
      nodes: CanvasNode[];
      flowCards: { id: string; title: string; description: string }[];
    };

export type ScenarioData = {
  key: ScenarioKey;
  label: string;
  accent: AccentTone;
  railTitle: string;
  railSubtitle: string;
  railCaption: string;
  switcherLabel: string;
  chatPanelTitle: string;
  groupName: string;
  missionTitle: string;
  missionDescription: string;
  intentBadge: string;
  confidence: string;
  contextQuality: string;
  messages: MessageItem[];
  workflow: WorkflowStep[];
  output: OutputData;
  contextSources: ContextItem[];
  sourceEvidence: EvidenceItem[];
  syncActions: SyncActionItem[];
};

export type WorkspaceData = {
  title: string;
  subtitle: string;
  statusBadges: HeaderBadge[];
  systemNote: string;
  scenarios: Record<ScenarioKey, ScenarioData>;
};
