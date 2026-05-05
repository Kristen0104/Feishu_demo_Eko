import type { Metadata } from "next";

import { AppsWorkspacePage } from "@/components/workspace/workspace-module-pages";
import { getSessionListPageData } from "@/lib/sync/live-session-list-data";

export const metadata: Metadata = {
  title: "应用 · Eko",
  description: "工作台应用与扩展",
};

export const dynamic = "force-dynamic";

export default async function AppsPage() {
  return <AppsWorkspacePage data={await getSessionListPageData()} />;
}
