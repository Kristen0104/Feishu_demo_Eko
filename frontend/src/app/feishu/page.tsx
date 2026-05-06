import type { Metadata } from "next";

import { FeishuMockPage } from "@/components/feishu/FeishuMockPage";

export const metadata: Metadata = {
  title: "飞书群聊（Mock） · Eko",
  description: "录屏用飞书群聊 mock 页面",
};

export default function FeishuPage() {
  return <FeishuMockPage />;
}

