export type SessionPageData = {
  id: string;
  title: string;
  mode: "chat" | "word" | "canvas";
  summary: string;
  sourceNotes: string[];
  steps: { title: string; state: "done" | "running" | "pending" }[];
};

export const sessionPageDataMap: Record<string, SessionPageData> = {
  "meeting-confirmation": {
    id: "meeting-confirmation",
    title: "飞书即时回复确认",
    mode: "chat",
    summary: "已识别为即时交互场景：在群内确认会议信息，不触发画布重绘。",
    sourceNotes: ["来源：飞书群聊上下文", "来源：最近 5 轮会话记忆", "状态：只读观摩可见"],
    steps: [
      { title: "意图识别（闲聊/QA）", state: "done" },
      { title: "卡片状态更新", state: "done" },
      { title: "群内即时回复", state: "running" },
      { title: "归档到 Bitable", state: "pending" }
    ]
  },
  "weekly-marketing-summary": {
    id: "weekly-marketing-summary",
    title: "每周营销总结",
    mode: "word",
    summary: "已识别为文稿创作场景：整合飞书讨论、Bitable 指标与 RAG 资料，生成结构化文稿。",
    sourceNotes: ["来源：飞书营销群对话（最近 50 条）", "来源：Bitable 渠道投放数据", "来源：RAG 周报模板（Top-5）"],
    steps: [
      { title: "意图识别（Word）", state: "done" },
      { title: "三源数据检索", state: "done" },
      { title: "文稿生成与微调", state: "running" },
      { title: "回流知识库 + 同步 Bitable", state: "pending" }
    ]
  },
  "q2-ads-review": {
    id: "q2-ads-review",
    title: "Q2 广告投放复盘",
    mode: "canvas",
    summary: "已识别为汇报演示场景：Agent 驱动画布自动布局，支持 PC/移动端实时同步浏览。",
    sourceNotes: ["来源：飞书群内汇报诉求", "来源：Bitable Q2 广告数据", "来源：RAG 过往复盘模板"],
    steps: [
      { title: "意图识别（PPT/Canvas）", state: "done" },
      { title: "三源数据检索", state: "done" },
      { title: "画布生长与布局", state: "running" },
      { title: "确认保存并归档", state: "pending" }
    ]
  }
};

export function getSessionPageData(id: string): SessionPageData {
  return sessionPageDataMap[id] ?? sessionPageDataMap["meeting-confirmation"];
}
