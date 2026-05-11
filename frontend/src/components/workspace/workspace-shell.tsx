"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/components/UiPrimitives";
import { WorkspaceChrome } from "@/components/workspace/workspace-chrome";
import { resolveWorkspaceBreadcrumb } from "@/lib/workspace-breadcrumb";
import { resolveWorkspaceNav } from "@/lib/workspace-nav";
import type { SessionListPageData } from "@/types/session";

/** 会话详情页和知识管理页由内层分栏自己管理滚动；其余工作台页面在主内容区纵向滚动 */
function isSessionDetailRoute(pathname: string) {
  return /^\/sessions\/[^/]+$/.test(pathname);
}

function usesInnerScrollLayout(pathname: string) {
  return isSessionDetailRoute(pathname) || pathname.startsWith("/knowledge");
}

export function WorkspaceShell({
  data,
  children,
}: {
  data: SessionListPageData;
  children: ReactNode;
}) {
  const pathname = usePathname() ?? "";
  const { activeNav } = resolveWorkspaceNav(pathname);
  const breadcrumb = resolveWorkspaceBreadcrumb(pathname);
  const clipInnerLayout = usesInnerScrollLayout(pathname);
  const contentKey = pathname.startsWith("/profile") ? `profile:${pathname}` : "workspace-content";

  return (
    <WorkspaceChrome data={data} breadcrumb={breadcrumb} activeNav={activeNav}>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <div
          key={contentKey}
          className={cn(
            "min-h-0 flex-1",
            clipInnerLayout ? "overflow-hidden" : "overflow-y-auto overflow-x-hidden overscroll-contain",
          )}
        >
          {children}
        </div>
      </div>
    </WorkspaceChrome>
  );
}
