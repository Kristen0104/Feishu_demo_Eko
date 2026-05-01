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
      <body className="min-h-screen bg-slate-950 antialiased text-slate-100">
        {children}
      </body>
    </html>
  );
}
