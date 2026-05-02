import type { Metadata } from "next";

import { AppsWorkspacePage } from "@/components/workspace/workspace-module-pages";
import { getSessionListPageData } from "@/lib/mock/session-list-data";

export const metadata: Metadata = {
  title: "应用 · Eko",
  description: "工作台应用与扩展",
};

export default function AppsPage() {
  return <AppsWorkspacePage data={getSessionListPageData()} />;
}
