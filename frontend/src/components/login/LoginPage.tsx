"use client";

import Link from "next/link";

const rows = [
  ["项目初始化", "Next.js 15 项目搭建、目录结构设计、依赖安装"],
  ["Dashboard", "会话列表页、会话详情页、登录页"],
  ["Tldraw 画布", "集成 Tldraw SDK，实现画布自动渲染、生长动效"],
  ["Word 预览", "Markdown 渲染、实时流式更新展示"],
  ["状态管理", "Zustand store 设计，多端状态同步逻辑"],
  ["WebSocket", "实时消息订阅、状态机更新 UI"],
  ["Framer Motion", "Agent 思考动画、元素入场动效"],
  ["三端适配", "响应式布局、Tauri/Capacitor 集成测试"],
];

export function LoginPage() {
  return (
    <div className="min-h-screen bg-[#f3f3f3] px-7 py-8 text-[#2b2b2b]">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-semibold tracking-tight">成员 A张欣怡：前端开发</h1>
          <Link href="/sessions" className="rounded-md border border-[#bfbfbf] bg-white px-3 py-1.5 text-sm text-[#333] hover:bg-[#f8f8f8]">
            进入 Dashboard
          </Link>
        </div>

        <div className="overflow-hidden border border-[#cfcfcf] bg-white">
          <table className="w-full border-collapse text-left text-base">
            <thead>
              <tr className="bg-[#f7f7f7]">
                <th className="w-[220px] border border-[#cfcfcf] px-5 py-3 font-semibold">模块</th>
                <th className="border border-[#cfcfcf] px-5 py-3 font-semibold">具体任务</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row[0]}>
                  <td className="border border-[#cfcfcf] px-5 py-3 font-semibold">{row[0]}</td>
                  <td className="border border-[#cfcfcf] px-5 py-3">{row[1]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
