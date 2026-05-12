import type { Metadata } from "next";

import { AuthBootstrap } from "@/components/AuthBootstrap";
import "./globals.css";

export const metadata: Metadata = {
  title: "Eko",
  description: "Feishu Eko demo",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "Eko",
    statusBarStyle: "default",
  },
};

export default function RootLayout(props: { children: React.ReactNode }) {
  const { children } = props;
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-950 antialiased text-slate-100">
        <AuthBootstrap />
        {children}
      </body>
    </html>
  );
}
