import { resolveWorkspaceNav } from "@/lib/workspace-nav";

export type WorkspaceBreadcrumbSegment = {
  label: string;
  /** When set, segment renders as a link. Omit on the current page segment. */
  href?: string;
  current?: boolean;
};

/**
 * Top header breadcrumb: Eko (→ /home) + module path.
 */
export function resolveWorkspaceBreadcrumb(
  pathname: string,
  options: { sessionTitle?: string | null } = {},
): WorkspaceBreadcrumbSegment[] {
  const path = pathname.split("?")[0] ?? pathname;

  const root: WorkspaceBreadcrumbSegment = { label: "Eko", href: "/home" };

  if (/^\/sessions\/[^/]+$/.test(path)) {
    return [root, { label: "会话", href: "/sessions" }, { label: options.sessionTitle?.trim() || "会话详情", current: true }];
  }

  if (path === "/sessions") {
    return [root, { label: "会话", current: true }];
  }

  const { pageLabel } = resolveWorkspaceNav(pathname);
  return [root, { label: pageLabel, current: true }];
}
