import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Eko",
  description: "Feishu Eko demo",
};

export default function RootLayout(props: { children: React.ReactNode }) {
  const { children } = props;
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-[#E8EDF6] antialiased text-slate-900">
        {children}
      </body>
    </html>
  );
}
