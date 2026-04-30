"use client";

import { sessionDetailData } from "@/lib/mock/session-detail-data";
import { SessionDetailData } from "@/types/session-detail";
import { DocSessionWorkspace } from "./DocSessionWorkspace";

export function SessionDetailShell({
  data = sessionDetailData,
}: {
  data?: SessionDetailData;
}) {
  return <DocSessionWorkspace data={data} />;
}
