import { SessionItem, SessionListPageData, SessionParticipant } from "@/types/session";

const people: Record<string, SessionParticipant> = {
  sarah: { id: "sarah", name: "Sarah Chen", initials: "SC" },
  ava: { id: "ava", name: "Ava", initials: "AV" },
  leo: { id: "leo", name: "Leo", initials: "LE" },
  mia: { id: "mia", name: "Mia", initials: "MI" },
  alex: { id: "alex", name: "Alex", initials: "AL" },
};

function members(ids: Array<keyof typeof people>) {
  return ids.map((id) => people[id]);
}

function buildItem(item: SessionItem): SessionItem {
  return item;
}

const fallbackData: SessionListPageData = {
  teamName: "飞书市场部",
  teamMembersLabel: "12 名成员",
  user: {
    name: "Sarah Chen",
    email: "sarah.chen@eko.ai",
    initials: "SC",
  },
  sections: [
    {
      title: "今天",
      items: [
        buildItem({
          id: "meeting-confirmation",
          title: "飞书即时回复确认",
          summary: "确认今日会议时间与提醒节奏，保持轻量即时回复。",
          source: "飞书",
          kind: "chat",
          kindLabel: "聊天",
          status: "进行中",
          updatedAt: "上午 9:13",
          participants: members(["mia", "leo"]),
          starred: true,
          preview: {
            id: "meeting-confirmation",
            title: "飞书即时回复确认",
            source: "飞书",
            startedAt: "今天 上午 9:12",
            outputMode: "聊天",
            status: "进行中",
            syncedAt: "今天 上午 9:13",
            summary: "针对会前确认问题完成即时回复，明确会议时间 3:30 与会前提醒节点。",
            collaborators: members(["mia", "leo"]),
            relatedItems: [
              { id: "r1", title: "会议确认记录", tone: "文稿", updatedAt: "更新于 5 月 11 日" },
              { id: "r2", title: "会前沟通串", tone: "聊天", updatedAt: "更新于 5 月 11 日" },
              { id: "r3", title: "会议事项清单", tone: "数据", updatedAt: "更新于 5 月 11 日" },
            ],
            activity: { id: "a1", actor: "Mia", action: "发起了会议确认", time: "刚刚" },
          },
        }),
        buildItem({
          id: "weekly-marketing-summary",
          title: "营销计划草稿 v3",
          summary: "已整合最新市场活动节奏与预算分配，待评审。",
          source: "飞书",
          kind: "doc",
          kindLabel: "文稿",
          status: "已同步",
          updatedAt: "上午 8:28",
          participants: members(["ava"]),
          preview: {
            id: "weekly-marketing-summary",
            title: "营销计划草稿 v3",
            source: "飞书",
            startedAt: "今天 上午 8:10",
            outputMode: "文稿",
            status: "已同步",
            syncedAt: "今天 上午 8:28",
            summary:
              "围绕新品营销主题整理预算、投放节奏与内容计划，产出结构化文稿以便开会评审与同步执行。",
            collaborators: members(["ava"]),
            relatedItems: [
              { id: "r4", title: "预算分配说明", tone: "文稿", updatedAt: "更新于 5 月 11 日" },
              { id: "r5", title: "渠道执行群纪要", tone: "聊天", updatedAt: "更新于 5 月 10 日" },
              { id: "r6", title: "周投放数据快照", tone: "数据", updatedAt: "更新于 5 月 10 日" },
            ],
            activity: { id: "a2", actor: "Ava", action: "同步了最新文稿", time: "1 小时前" },
          },
        }),
        buildItem({
          id: "q2-ads-review",
          title: "Q2 广告投放复盘",
          summary: "我们先回顾各渠道的投放表现，再讨论优化方向。",
          source: "飞书",
          kind: "chat",
          kindLabel: "聊天",
          status: "进行中",
          updatedAt: "上午 9:42",
          participants: members(["sarah", "leo", "mia"]),
          preview: {
            id: "q2-ads-review",
            title: "Q2 广告投放复盘",
            source: "飞书",
            startedAt: "今天 上午 9:35",
            outputMode: "聊天",
            status: "进行中",
            syncedAt: "今天 上午 9:42",
            summary:
              "复盘 Q2 各渠道广告投放表现，分析投放效果与转化情况，讨论人群、创意与预算分配的优化方向，并输出下一步行动计划。",
            collaborators: members(["sarah", "leo", "mia"]),
            relatedItems: [
              { id: "r7", title: "营销计划草稿 v3", tone: "文稿", updatedAt: "更新于 5 月 11 日" },
              { id: "r8", title: "付费搜索表现回顾", tone: "聊天", updatedAt: "更新于 5 月 9 日" },
              { id: "r9", title: "投放数据看板 Q2", tone: "数据", updatedAt: "更新于 5 月 8 日" },
            ],
            activity: { id: "a3", actor: "Sarah Chen", action: "继续了此会话", time: "23 分钟前" },
          },
        }),
      ],
    },
    {
      title: "昨天",
      items: [
        buildItem({
          id: "new-product-launch",
          title: "新品发布信息梳理",
          summary: "汇总新品卖点、定价策略与上市节奏，供发布会使用。",
          source: "飞书",
          kind: "doc",
          kindLabel: "文稿",
          status: "已同步",
          updatedAt: "5 月 11 日",
          participants: members(["ava", "mia"]),
          preview: {
            id: "new-product-launch",
            title: "新品发布信息梳理",
            source: "飞书",
            startedAt: "昨天 下午 3:10",
            outputMode: "文稿",
            status: "已同步",
            syncedAt: "昨天 下午 4:20",
            summary: "整理新品卖点、上市节奏和对外口径，供市场发布与销售沟通使用。",
            collaborators: members(["ava", "mia"]),
            relatedItems: [],
            activity: { id: "a4", actor: "Mia", action: "完成了文稿同步", time: "昨天" },
          },
        }),
        buildItem({
          id: "website-brief",
          title: "网站内容 Brief",
          summary: "明确页面结构、核心信息与落地页内容方向。",
          source: "IM",
          kind: "doc",
          kindLabel: "文稿",
          status: "草稿",
          updatedAt: "5 月 11 日",
          participants: members(["sarah"]),
          preview: {
            id: "website-brief",
            title: "网站内容 Brief",
            source: "IM",
            startedAt: "昨天 上午 11:00",
            outputMode: "文稿",
            status: "草稿",
            syncedAt: "昨天 上午 11:20",
            summary: "围绕官网改版目标输出结构化内容 brief，当前仍在补充案例与转化链路。",
            collaborators: members(["sarah"]),
            relatedItems: [],
            activity: { id: "a5", actor: "Sarah Chen", action: "更新了页面结构", time: "昨天" },
          },
        }),
        buildItem({
          id: "gtm-workshop",
          title: "Q3 GTM 策略工作坊",
          summary: "梳理 Q3 重点市场与增长策略，明确执行优先级。",
          source: "飞书",
          kind: "canvas",
          kindLabel: "画布",
          status: "进行中",
          updatedAt: "5 月 11 日",
          participants: members(["ava", "leo", "mia", "alex"]),
          preview: {
            id: "gtm-workshop",
            title: "Q3 GTM 策略工作坊",
            source: "飞书",
            startedAt: "昨天 上午 9:30",
            outputMode: "画布",
            status: "进行中",
            syncedAt: "昨天 下午 1:00",
            summary: "围绕 Q3 市场策略搭建协作画布，突出关键动作、优先级与负责人分工。",
            collaborators: members(["ava", "leo", "mia", "alex"]),
            relatedItems: [],
            activity: { id: "a6", actor: "Alex", action: "继续推进了画布草案", time: "昨天" },
          },
        }),
      ],
    },
    {
      title: "本周更早",
      items: [
        buildItem({
          id: "competitor-analysis",
          title: "竞品分析总结",
          summary: "总结核心竞品的功能、定价与差异化策略。",
          source: "飞书",
          kind: "doc",
          kindLabel: "文稿",
          status: "已同步",
          updatedAt: "5 月 10 日",
          participants: members(["ava"]),
          preview: {
            id: "competitor-analysis",
            title: "竞品分析总结",
            source: "飞书",
            startedAt: "5 月 10 日",
            outputMode: "文稿",
            status: "已同步",
            syncedAt: "5 月 10 日",
            summary: "梳理竞品策略、定价与能力差异，形成对外沟通和内部策略输入。",
            collaborators: members(["ava"]),
            relatedItems: [],
            activity: { id: "a7", actor: "Ava", action: "完成竞品文稿", time: "5 月 10 日" },
          },
        }),
        buildItem({
          id: "paid-search-review",
          title: "付费搜索表现回顾",
          summary: "回顾关键词表现与转化，探讨下一步优化方向。",
          source: "IM",
          kind: "chat",
          kindLabel: "聊天",
          status: "待处理",
          updatedAt: "5 月 9 日",
          participants: members(["sarah"]),
          preview: {
            id: "paid-search-review",
            title: "付费搜索表现回顾",
            source: "IM",
            startedAt: "5 月 9 日",
            outputMode: "聊天",
            status: "待处理",
            syncedAt: "5 月 9 日",
            summary: "回顾投放关键词与转化情况，准备进入下一轮对话澄清和优化。",
            collaborators: members(["sarah"]),
            relatedItems: [],
            activity: { id: "a8", actor: "Sarah Chen", action: "等待下一步处理", time: "5 月 9 日" },
          },
        }),
        buildItem({
          id: "user-persona-map",
          title: "用户画像映射",
          summary: "映射核心用户画像及旅程，识别关键触点。",
          source: "飞书",
          kind: "canvas",
          kindLabel: "画布",
          status: "草稿",
          updatedAt: "5 月 9 日",
          participants: members(["mia"]),
          preview: {
            id: "user-persona-map",
            title: "用户画像映射",
            source: "飞书",
            startedAt: "5 月 9 日",
            outputMode: "画布",
            status: "草稿",
            syncedAt: "5 月 9 日",
            summary: "围绕用户画像与旅程节点搭建结构化画布，为内容和转化策略提供依据。",
            collaborators: members(["mia"]),
            relatedItems: [],
            activity: { id: "a9", actor: "Mia", action: "创建了画像画布草稿", time: "5 月 9 日" },
          },
        }),
      ],
    },
  ],
};

function isValidStatus(status: unknown): status is SessionItem["status"] {
  return status === "已同步" || status === "进行中" || status === "草稿" || status === "待处理";
}

function isValidKind(kind: unknown): kind is SessionItem["kind"] {
  return kind === "chat" || kind === "doc" || kind === "canvas";
}

function sanitizeItem(item: SessionItem): SessionItem | null {
  if (!item?.id || !item.title || !item.summary || !isValidKind(item.kind) || !isValidStatus(item.status)) {
    return null;
  }
  return item;
}

export function getSessionListPageData(): SessionListPageData {
  const safeSections = fallbackData.sections
    .map((section) => ({
      ...section,
      items: section.items.map(sanitizeItem).filter((item): item is SessionItem => Boolean(item)),
    }))
    .filter((section) => section.items.length > 0);

  if (!safeSections.length) {
    return fallbackData;
  }

  return {
    ...fallbackData,
    sections: safeSections,
  };
}

export function getDefaultSessionId(data: SessionListPageData = getSessionListPageData()) {
  return data.sections[0]?.items[0]?.id ?? "q2-ads-review";
}
