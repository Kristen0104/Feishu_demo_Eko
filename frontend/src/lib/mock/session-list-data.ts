/**
 * 会话列表 Mock（与 session-detail-data 中的 session id 对齐）
 */

export type SessionListItem = {
  id: string;
  title: string;
  summary: string;
  intent: "chat" | "word" | "canvas";
  intentLabel: string;
  updatedAtLabel: string;
  stateLabel: string;
};

export const sessionListItems: SessionListItem[] = [
  {
    id: "meeting-confirmation",
    title: "飞书即时回复确认",
    summary: "即时交互 / 群内时间确认与会前提醒，避免刷屏干扰。",
    intent: "chat",
    intentLabel: "闲聊 / QA",
    updatedAtLabel: "更新于 · 刚刚",
    stateLabel: "演示就绪",
  },
  {
    id: "weekly-marketing-summary",
    title: "每周营销总结",
    summary: "文稿创作 · 汇总飞书上下文、Bitable 指标与周报素材。",
    intent: "word",
    intentLabel: "文稿 Word",
    updatedAtLabel: "更新于 · 9 分钟前",
    stateLabel: "生成中",
  },
  {
    id: "q2-ads-review",
    title: "Q2 广告投放复盘",
    summary: "演示画布 · Agent 驱动的画布排版与多端预览（Mock）。",
    intent: "canvas",
    intentLabel: "画布 PPT",
    updatedAtLabel: "更新于 · 昨日",
    stateLabel: "待确认",
  },
];
