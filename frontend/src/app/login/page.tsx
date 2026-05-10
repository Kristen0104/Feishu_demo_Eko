import type { Metadata } from "next";

import { LoginPage } from "@/components/login/LoginPage";

export const metadata: Metadata = {
  title: "登录 · Eko",
  description: "Eko 工作台登录",
};

type LoginSearchParams = Promise<{ registered?: string | string[] }>;

/** 在服务端读取查询参数，避免客户端 useSearchParams 触发长时间 Suspense（开发环境易被误认为「一直加载」） */
export default async function LoginRoutePage(props: { searchParams: LoginSearchParams }) {
  const searchParams = await props.searchParams;
  const registered = searchParams.registered;
  const justRegistered =
    registered === "1" || (Array.isArray(registered) && registered.includes("1"));

  return <LoginPage justRegistered={justRegistered} />;
}
