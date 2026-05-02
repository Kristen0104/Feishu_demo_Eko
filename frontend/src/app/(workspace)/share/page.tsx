import type { Metadata } from "next";

import { ShareCollaborationPage } from "@/components/workspace/workspace-module-pages";
import { getSessionListPageData } from "@/lib/mock/session-list-data";

export const metadata: Metadata = {
  title: "分享 / 协作 · Eko",
  description: "共享链接与协作者",
};

export default function SharePage() {
  return <ShareCollaborationPage data={getSessionListPageData()} />;
}
