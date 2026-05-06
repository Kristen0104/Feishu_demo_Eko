import type { Metadata } from "next";

import { SettingsWorkspacePage } from "@/components/settings/SettingsWorkspacePage";
import { getSessionListPageData } from "@/lib/sync/live-session-list-data";

export const metadata: Metadata = {
  title: "设置 · Eko",
  description: "账户与偏好入口",
};

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  return <SettingsWorkspacePage data={await getSessionListPageData()} />;
}
