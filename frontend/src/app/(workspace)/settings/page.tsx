import type { Metadata } from "next";

import { SettingsWorkspacePage } from "@/components/settings/SettingsWorkspacePage";
import { getSessionListPageData } from "@/lib/mock/session-list-data";

export const metadata: Metadata = {
  title: "设置 · Eko",
  description: "账户与偏好入口",
};

export default function SettingsPage() {
  return <SettingsWorkspacePage data={getSessionListPageData()} />;
}
