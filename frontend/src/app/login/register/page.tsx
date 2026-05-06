import type { Metadata } from "next";

import { CreateAccountPage } from "@/components/login/CreateAccountPage";

export const metadata: Metadata = {
  title: "创建账号 · Eko",
  description: "注册 Eko 工作区账号",
};

export default function RegisterRoutePage() {
  return <CreateAccountPage />;
}
