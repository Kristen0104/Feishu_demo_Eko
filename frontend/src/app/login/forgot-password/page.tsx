import type { Metadata } from "next";

import { ForgotPasswordPage } from "@/components/login/ForgotPasswordPage";

export const metadata: Metadata = {
  title: "重设密码 · Eko",
  description: "Eko 工作区密码重设",
};

export default function ForgotPasswordRoutePage() {
  return <ForgotPasswordPage />;
}
