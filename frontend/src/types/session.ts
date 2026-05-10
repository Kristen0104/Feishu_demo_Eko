export type SessionKind = "chat" | "doc" | "canvas";

export type SessionStatus = "已同步" | "进行中" | "草稿" | "待处理";

export type SessionSource = "飞书" | "IM";

export type SessionParticipant = {
  id: string;
  name: string;
  initials: string;
};

export type SessionRelatedItem = {
  id: string;
  title: string;
  tone: "文稿" | "聊天" | "数据";
  updatedAt: string;
};

export type SessionActivity = {
  id: string;
  actor: string;
  action: string;
  time: string;
};

export type SessionPreview = {
  id: string;
  title: string;
  source: SessionSource;
  startedAt: string;
  outputMode: "聊天" | "文稿" | "画布";
  status: SessionStatus;
  syncedAt: string;
  summary: string;
  collaborators: SessionParticipant[];
  relatedItems: SessionRelatedItem[];
  activity: SessionActivity;
  externalUrl?: string;
};

export type SessionItem = {
  id: string;
  title: string;
  summary: string;
  source: SessionSource;
  kind: SessionKind;
  kindLabel: "聊天" | "文稿" | "画布";
  status: SessionStatus;
  updatedAt: string;
  participants: SessionParticipant[];
  starred?: boolean;
  preview: SessionPreview;
};

export type SessionSection = {
  title: string;
  items: SessionItem[];
};

export type SessionListPageData = {
  teamName: string;
  teamMembersLabel: string;
  user: {
    name: string;
    email: string;
    initials: string;
  };
  sections: SessionSection[];
};
