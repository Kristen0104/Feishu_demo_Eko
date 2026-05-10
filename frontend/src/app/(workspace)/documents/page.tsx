import type { Metadata } from "next";

import { DocumentsWorkspacePage } from "@/components/documents/DocumentsWorkspacePage";
import { getSessionListPageData } from "@/lib/sync/live-session-list-data";

export const metadata: Metadata = {
  title: "文档 · Eko",
  description: "文稿与飞书文档一览",
};

export const dynamic = "force-dynamic";

export default async function DocumentsPage() {
  return <DocumentsWorkspacePage data={await getSessionListPageData()} />;
}
