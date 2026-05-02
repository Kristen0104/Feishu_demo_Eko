import type { ReactNode } from "react";

import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { getSessionListPageData } from "@/lib/mock/session-list-data";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const data = getSessionListPageData();
  return <WorkspaceShell data={data}>{children}</WorkspaceShell>;
}
