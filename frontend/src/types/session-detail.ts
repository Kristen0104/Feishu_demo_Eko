import { AccentTone, HeaderBadge, WorkflowStatus, WorkflowStep } from "@/types/workspace";

export type DetailTabKey = "chat" | "doc" | "canvas";

export type DetailNavItem = {
  id: string;
  label: string;
  icon: "home" | "chat" | "doc" | "share" | "task" | "team" | "apps" | "settings";
  active?: boolean;
};

export type DetailMessageFileCard = {
  title: string;
  typeLabel: string;
  statusLabel: string;
};

export type DetailMessageActionButton = {
  label: string;
  tone?: "default" | "primary" | "success";
};

export type DetailMessageActionCard = {
  title: string;
  description?: string;
  buttons: DetailMessageActionButton[];
};

export type DetailMessagePlannerCard = {
  goal: string;
  intent: string;
  taskComplexity?: string;
  missingInfo?: string[];
  needClarification?: boolean;
  questions?: string[];
  assumptions?: string[];
  clarificationNeeded?: boolean;
  clarificationQuestion?: string | null;
  summary: string;
  steps: Array<{
    id: string;
    title: string;
    description?: string;
    type?: string;
    tool?: string;
    input?: Record<string, unknown>;
    expectedOutput?: string;
    dependsOn?: string[];
  }>;
  finalOutput?: {
    format: string;
    requirements: string[];
  };
};

export type DetailMessage = {
  id: string;
  author: string;
  role: "member" | "eko";
  time: string;
  body: string;
  avatar: string;
  mention?: string;
  sent?: boolean;
  helperText?: string;
  fileCard?: DetailMessageFileCard;
  actionCard?: DetailMessageActionCard;
  plannerCard?: DetailMessagePlannerCard;
};

export type DetailSourceItem = {
  id: string;
  title: string;
  description: string;
  status: WorkflowStatus;
};

export type DetailContextMessage = {
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

export type DetailEvidenceItem = {
  id: string;
  title: string;
  description: string;
  tone: "chat" | "document" | "record";
};

export type DetailSyncAction = {
  id: string;
  title: string;
  status: WorkflowStatus;
};

export type DetailOutputTab = {
  key: DetailTabKey;
  label: string;
  accent: AccentTone;
};

export type DetailDocumentSection = {
  title: string;
  body?: string;
  bullets?: string[];
};

export type DetailArtifactKind = "ppt" | "docx" | "board";

export type DetailDocumentArtifact = {
  kind?: DetailArtifactKind | string | null;
  intent?: string | null;
  title?: string | null;
  jobId?: string | null;
  status?: string | null;
  progress?: number | null;
  currentStep?: string | null;
  downloadUrl?: string | null;
  errorMessage?: string | null;
  content?: string | null;
  sharingUrl?: string | null;
  whiteboardId?: string | null;
  previewUrl?: string | null;
  resultSummary?: string | null;
  bitableArchiveResults?: Array<{
    source_id?: string | null;
    record_id?: string | null;
    record_url?: string | null;
    status?: string | null;
    message?: string | null;
    error?: string | null;
  }> | null;
};

export type DetailDocumentTableRow = {
  campaign: string;
  channel: string;
  visits: string;
  leads: string;
  conversion: string;
  roi: string;
  budget: string;
};

export type DetailCanvasNode = {
  id: string;
  index: number;
  title: string;
  bullets: string[];
  icon: "trend" | "rocket" | "calendar" | "spark" | "alert" | "check";
  status?: "default" | "draft";
};

export type DetailPhaseCard = {
  id: string;
  title: string;
  subtitle?: string;
  timestamp?: string;
  tag?: string;
  status: WorkflowStatus;
};

export type DetailRelatedFile = {
  id: string;
  title: string;
  updatedAt: string;
  tone: "doc" | "sheet" | "deck";
};

export type DetailActivity = {
  id: string;
  title: string;
  time: string;
  tone: "doc" | "route" | "data" | "session";
};

export type SessionDetailData = {
  id: string;
  layoutVariant: "chat" | "doc" | "canvas";
  title: string;
  breadcrumb: string[];
  topBadges: HeaderBadge[];
  navItems: DetailNavItem[];
  assistantName: string;
  assistantEmail: string;
  conversationTitle: string;
  messages: DetailMessage[];
  missionTitle: string;
  missionBadges: string[];
  missionSubtitle: string;
  confidence: string;
  contextQuality: string;
  workflow: WorkflowStep[];
  outputTabs: DetailOutputTab[];
  defaultTab: DetailTabKey;
  chatReply: {
    title: string;
    body: string;
    source: string;
  };
  document: {
    title: string;
    date: string;
    markdown?: string | null;
    sections: DetailDocumentSection[];
    tableRows?: DetailDocumentTableRow[];
    artifact?: DetailDocumentArtifact;
  };
  canvas: {
    title: string;
    nodes: DetailCanvasNode[];
    artifact?: DetailDocumentArtifact;
  };
  artifact?: DetailDocumentArtifact;
  intent?: string | null;
  disabledCards: Array<{ title: string; subtitle: string }>;
  contextSources: DetailSourceItem[];
  contextMessages?: DetailContextMessage[];
  instruction?: string | null;
  sourceEvidence: DetailEvidenceItem[];
  syncActions: DetailSyncAction[];
  statusBadges: HeaderBadge[];
  systemNote: string;
  actionButtons: string[];
  workflowCards?: DetailPhaseCard[];
  progress?: number;
  relatedFiles?: DetailRelatedFile[];
  memoryNote?: {
    title: string;
    body: string;
    action: string;
  };
  syncOverview?: {
    statusLabel: string;
    items: string[];
  };
  activities?: DetailActivity[];
};
