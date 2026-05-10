import { resolveWorkspaceNav } from "@/lib/workspace-nav";

export type WorkspaceBreadcrumbSegment = {
  label: string;
  /** When set, segment renders as a link. Omit on the current page segment. */
  href?: string;
  current?: boolean;
};

/**
 * Top header breadcrumb: Eko (→ /home) + module path + optional session title on `/sessions/[slug]`.
 */
export function resolveWorkspaceBreadcrumb(pathname: string): WorkspaceBreadcrumbSegment[] {
  const path = pathname.split("?")[0] ?? pathname;

  const root: WorkspaceBreadcrumbSegment = { label: "Eko", href: "/home" };

  const sessionDetailMatch = /^\/sessions\/([^/]+)$/.exec(path);
  if (sessionDetailMatch?.[1]) {
    const slug = sessionDetailMatch[1];
    return [root, { label: "会话", href: "/sessions" }, { label: slug, current: true }];
  }

  if (path === "/sessions") {
    return [root, { label: "会话", current: true }];
  }

  const { pageLabel } = resolveWorkspaceNav(pathname);
  return [root, { label: pageLabel, current: true }];
}
