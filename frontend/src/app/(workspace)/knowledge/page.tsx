import type { Metadata } from "next";

import { KnowledgeWorkspacePage } from "@/components/knowledge/KnowledgeWorkspacePage";

export const metadata: Metadata = {
  title: "知识库 · Eko",
  description: "RAG 知识库文件导入与检索",
};

export const dynamic = "force-dynamic";

export default function KnowledgePage() {
  return <KnowledgeWorkspacePage />;
}
