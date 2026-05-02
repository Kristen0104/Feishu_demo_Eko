import type { Metadata } from "next";

import { TeamWorkspacePage } from "@/components/workspace/workspace-module-pages";
import { getSessionListPageData } from "@/lib/mock/session-list-data";

export const metadata: Metadata = {
  title: "团队 · Eko",
  description: "成员与角色",
};

export default function TeamPage() {
  return <TeamWorkspacePage data={getSessionListPageData()} />;
}
