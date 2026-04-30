import { getSessionDetailData } from "@/lib/mock/session-detail-data";
import { SessionWorkspace } from "./SessionWorkspace";

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <SessionWorkspace data={getSessionDetailData(id)} />;
}
