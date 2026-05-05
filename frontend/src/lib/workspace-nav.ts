export type WorkspaceNavKey =
  | "home"
  | "sessions"
  | "documents"
  | "knowledge"
  | "share"
  | "tasks"
  | "team"
  | "apps"
  | "settings";

const LABELS: Record<WorkspaceNavKey, string> = {
  home: "主页",
  sessions: "会话",
  documents: "文档",
  knowledge: "知识库",
  share: "分享 / 协作",
  tasks: "任务",
  team: "团队",
  apps: "应用",
  settings: "设置",
};

/** Breadcrumb label shown in the top bar for the current route. */
export function resolveWorkspaceNav(pathname: string): { activeNav: WorkspaceNavKey; pageLabel: string } {
  const path = pathname.split("?")[0] ?? pathname;

  if (path === "/home") return { activeNav: "home", pageLabel: LABELS.home };
  if (path.startsWith("/sessions")) return { activeNav: "sessions", pageLabel: LABELS.sessions };
  if (path.startsWith("/documents")) return { activeNav: "documents", pageLabel: LABELS.documents };
  if (path.startsWith("/knowledge")) return { activeNav: "knowledge", pageLabel: LABELS.knowledge };
  if (path.startsWith("/share")) return { activeNav: "share", pageLabel: LABELS.share };
  if (path.startsWith("/tasks")) return { activeNav: "tasks", pageLabel: LABELS.tasks };
  if (path.startsWith("/team")) return { activeNav: "team", pageLabel: LABELS.team };
  if (path.startsWith("/apps")) return { activeNav: "apps", pageLabel: LABELS.apps };
  if (path.startsWith("/settings")) return { activeNav: "settings", pageLabel: LABELS.settings };
  if (path.startsWith("/profile")) return { activeNav: "settings", pageLabel: LABELS.settings };

  return { activeNav: "home", pageLabel: "工作台" };
}
