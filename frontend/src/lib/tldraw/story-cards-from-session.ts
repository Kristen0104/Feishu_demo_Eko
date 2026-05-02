import { getSessionDetailData } from "@/lib/mock/session-detail-data";

import type { StoryCardSpec } from "@/lib/tldraw/growth-storyboard";

const FALLBACK: StoryCardSpec[] = [
  { title: "问题与目标", subtitle: "对齐背景、约束与成功标准", accent: "violet" },
  { title: "方案结构", subtitle: "模块拆分与信息流", accent: "blue" },
  { title: "风险与指标", subtitle: "监控项与预警阈值", accent: "violet" },
  { title: "下一步", subtitle: "会后动作与负责人", accent: "blue" },
];

/**
 * 根据会话 mock（canvas.nodes）生成故事板文案；无节点时回退到 FALLBACK。
 * sessionId 为空时使用默认会话 meeting-confirmation。
 */
export function storyCardsFromSessionQuery(sessionId: string | null): StoryCardSpec[] {
  const id = sessionId?.trim() || "meeting-confirmation";
  const data = getSessionDetailData(id);
  const nodes = data.canvas?.nodes ?? [];
  if (nodes.length === 0) return FALLBACK;

  return nodes.map((n, i) => ({
    title: n.title,
    subtitle: n.bullets.slice(0, 4).join(" · "),
    accent: i % 2 === 0 ? "violet" : "blue",
  }));
}
