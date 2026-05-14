import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ProfileShell } from "@/components/profile/ProfileShell";

export const metadata: Metadata = {
  title: "个人资料 · Eko",
  description: "查看并管理个人资料与偏好",
};

export default function ProfileLayout({ children }: { children: ReactNode }) {
  return <ProfileShell>{children}</ProfileShell>;
}
