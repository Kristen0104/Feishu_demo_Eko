import type { Metadata } from "next";

import { HomeDashboardView } from "@/components/home/HomeDashboardView";
import { getSessionListPageData } from "@/lib/mock/session-list-data";

export const metadata: Metadata = {
  title: "主页 · Eko",
  description: "Eko Workspace · 工作台概览",
};

export default function HomePage() {
  return <HomeDashboardView data={getSessionListPageData()} />;
}
