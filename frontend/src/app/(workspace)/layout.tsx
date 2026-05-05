import type { ReactNode } from "react";

import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { getSessionListPageData } from "@/lib/sync/live-session-list-data";

export const dynamic = "force-dynamic";

export default async function WorkspaceLayout({ children }: { children: ReactNode }) {
  const data = await getSessionListPageData();
  return <WorkspaceShell data={data}>{children}</WorkspaceShell>;
}
