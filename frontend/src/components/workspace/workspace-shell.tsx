"use client";

import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { cn } from "@/components/UiPrimitives";
import { WorkspaceChrome } from "@/components/workspace/workspace-chrome";
import { authUserToProfilePatch, fetchCurrentAuthUser } from "@/lib/profile-api";
import { resolveWorkspaceBreadcrumb } from "@/lib/workspace-breadcrumb";
import { resolveWorkspaceNav } from "@/lib/workspace-nav";
import { useAppStore } from "@/store/app-store";
import { useProfileStore } from "@/store/profile-store";
import type { SessionListPageData } from "@/types/session";

/** 会话详情页由内层三栏自己管理滚动；其余工作台页面在主内容区纵向滚动 */
function isSessionDetailRoute(pathname: string) {
  return /^\/sessions\/[^/]+$/.test(pathname);
}

function sessionIdFromPathname(pathname: string): string | null {
  const match = pathname.match(/^\/sessions\/([^/]+)$/);
  if (!match) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}

function findSessionTitle(data: SessionListPageData, sessionId: string | null): string | null {
  if (!sessionId) return null;
  for (const section of data.sections) {
    const item = section.items.find((entry) => entry.id === sessionId);
    if (item?.title) return item.title;
  }
  return null;
}

export function WorkspaceShell({
  data,
  children,
}: {
  data: SessionListPageData;
  children: ReactNode;
}) {
  const pathname = usePathname() ?? "";
  const [liveUser, setLiveUser] = useState<SessionListPageData["user"] | null>(null);
  const profileOverrides = useProfileStore((state) => state.profileOverrides);
  const { activeNav } = resolveWorkspaceNav(pathname);
  const sessionId = sessionIdFromPathname(pathname);
  const runtimeSessionTitle = useAppStore((state) => (sessionId ? state.runtimeSessionMap[sessionId]?.title : null));
  const sessionTitle = runtimeSessionTitle || findSessionTitle(data, sessionId);
  const breadcrumb = resolveWorkspaceBreadcrumb(pathname, { sessionTitle });
  const clipInnerLayout = isSessionDetailRoute(pathname);
  const contentKey = pathname.startsWith("/profile") ? `profile:${pathname}` : "workspace-content";
  const chromeData = useMemo<SessionListPageData>(() => {
    const user = {
      ...data.user,
      ...(liveUser ?? {}),
    };
    const overrideName = profileOverrides.displayName?.trim();
    const overrideEmail = profileOverrides.email?.trim();
    const overrideAvatar = profileOverrides.avatarUrl?.trim();
    const overrideInitials = profileOverrides.initials?.trim();
    return {
      ...data,
      user: {
        ...user,
        name: overrideName || user.name,
        email: overrideEmail || user.email,
        avatarUrl: overrideAvatar || user.avatarUrl,
        initials: overrideInitials || user.initials,
      },
    };
  }, [data, liveUser, profileOverrides]);

  useEffect(() => {
    let alive = true;
    void fetchCurrentAuthUser()
      .then((user) => {
        if (!alive) return;
        const patch = authUserToProfilePatch(user);
        setLiveUser({
          name: patch.displayName || data.user.name,
          email: patch.email || data.user.email,
          initials: patch.initials || data.user.initials,
          avatarUrl: patch.avatarUrl || "",
        });
      })
      .catch(() => {
        /* Keep server-rendered workspace identity when auth is unavailable. */
      });
    return () => {
      alive = false;
    };
  }, [data.user.avatarUrl, data.user.email, data.user.initials, data.user.name]);

  return (
    <WorkspaceChrome data={chromeData} breadcrumb={breadcrumb} activeNav={activeNav}>
      <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <div
          key={contentKey}
          className={cn(
            "h-full min-h-0 flex-1",
            clipInnerLayout ? "overflow-hidden" : "overflow-y-auto overflow-x-hidden overscroll-contain",
          )}
        >
          {children}
        </div>
      </div>
    </WorkspaceChrome>
  );
}
