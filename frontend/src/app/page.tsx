import { redirect } from "next/navigation";

/** 落地页进入登录，完成「登录 → 会话列表 → 会话详情」演示路径 */
export default function RootPage() {
  redirect("/login");
}
