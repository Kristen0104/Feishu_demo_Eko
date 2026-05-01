import { SessionDetailShell } from "@/components/session-detail/SessionDetailShell";
import { getSessionDetailData } from "@/lib/mock/session-detail-data";

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <SessionDetailShell data={getSessionDetailData(id)} />;
}
