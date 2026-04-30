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
};

export type DetailSourceItem = {
  id: string;
  title: string;
  description: string;
  status: WorkflowStatus;
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
    sections: DetailDocumentSection[];
    tableRows?: DetailDocumentTableRow[];
  };
  canvas: {
    title: string;
    nodes: DetailCanvasNode[];
  };
  disabledCards: Array<{ title: string; subtitle: string }>;
  contextSources: DetailSourceItem[];
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
