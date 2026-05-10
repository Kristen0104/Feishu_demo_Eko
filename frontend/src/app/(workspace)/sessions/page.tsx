import type { Metadata } from "next";

import { SessionsWorkspace } from "@/components/sessions/SessionsWorkspace";
import { getSessionListPageData } from "@/lib/sync/live-session-list-data";

export const metadata: Metadata = {
  title: "会话列表 · Eko",
  description: "Eko Workspace · 会话列表",
};

export default async function SessionsListPage() {
  const data = await getSessionListPageData();
  return <SessionsWorkspace initialSections={data.sections} />;
}
