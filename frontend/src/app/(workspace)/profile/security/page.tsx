import type { Metadata } from "next";

import { ProfileSecurityPage } from "@/components/profile/ProfileSecurityPage";

export const metadata: Metadata = {
  title: "账号与安全 · Eko",
  description: "密码与登录设备（演示）",
};

export default function ProfileSecurityRoutePage() {
  return <ProfileSecurityPage />;
}
