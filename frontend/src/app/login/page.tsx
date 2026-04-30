import type { Metadata } from "next";

import { LoginPage } from "@/components/login/LoginPage";

export const metadata: Metadata = {
  title: "登录 · Eko",
  description: "Eko 工作台登录（演示）",
};

export default function LoginRoutePage() {
  return <LoginPage />;
}
