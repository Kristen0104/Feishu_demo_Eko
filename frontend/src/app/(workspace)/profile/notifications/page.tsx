import type { Metadata } from "next";

import { ProfileNotificationsPage } from "@/components/profile/ProfileNotificationsPage";

export const metadata: Metadata = {
  title: "通知设置 · Eko",
  description: "通知偏好（演示）",
};

export default function ProfileNotificationsRoutePage() {
  return <ProfileNotificationsPage />;
}
