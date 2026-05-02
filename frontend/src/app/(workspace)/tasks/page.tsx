import type { Metadata } from "next";

import { TasksWorkspacePage } from "@/components/workspace/workspace-module-pages";
import { getSessionListPageData } from "@/lib/mock/session-list-data";

export const metadata: Metadata = {
  title: "任务 · Eko",
  description: "跨模块任务列表",
};

export default function TasksPage() {
  return <TasksWorkspacePage data={getSessionListPageData()} />;
}
