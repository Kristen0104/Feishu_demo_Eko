import { SessionDetailData } from "@/types/session-detail";

const topBadges = [
  { label: "演示就绪", tone: "success" as const },
  { label: "模拟模式", tone: "info" as const },
  { label: "实时连接待接入", tone: "neutral" as const },
];

const navItems = [
  { id: "home", label: "主页", icon: "home" as const },
  { id: "chat", label: "会话", icon: "chat" as const, active: true },
  { id: "doc", label: "文档", icon: "doc" as const },
  { id: "share", label: "分享 / 协作", icon: "share" as const },
  { id: "task", label: "任务", icon: "task" as const },
  { id: "team", label: "团队", icon: "team" as const },
  { id: "apps", label: "应用", icon: "apps" as const },
  { id: "settings", label: "设置", icon: "settings" as const },
];

const commonTabs = [
  { key: "chat" as const, label: "聊天", accent: "chat" as const },
  { key: "doc" as const, label: "文稿", accent: "doc" as const },
  { key: "canvas" as const, label: "画布", accent: "canvas" as const },
];

export const sessionDetailDataMap: Record<string, SessionDetailData> = {
  "meeting-confirmation": {
    id: "meeting-confirmation",
    layoutVariant: "chat",
    title: "飞书即时回复确认",
    breadcrumb: ["Eko", "会话", "飞书即时回复确认"],
    topBadges,
    navItems,
    assistantName: "Sarah Chen",
    assistantEmail: "在线",
    conversationTitle: "对话",
    messages: [
      {
        id: "m1",
        author: "Mia",
        role: "member",
        time: "09:12",
        body: "大家下午开会时间再确认一下，Eko demo 到底几点？",
        avatar: "M",
      },
      {
        id: "m2",
        author: "Leo",
        role: "member",
        time: "09:13",
        mention: "@Eko",
        body: "咱们下午几点开会？顺便提醒一下今天要确认其他设置。",
        avatar: "L",
      },
      {
        id: "m3",
        author: "Eko",
        role: "eko",
        time: "09:13",
        body: "今天下午 3:30 在产品组飞书会议室，建议仅安排 20 分钟。我会在 3:25 再同步一次提醒。",
        avatar: "E",
        sent: true,
      },
      {
        id: "m4",
        author: "Mia",
        role: "member",
        time: "09:14",
        body: "收到，谢谢！",
        avatar: "M",
      },
    ],
    missionTitle: "飞书即时回复确认",
    missionBadges: ["飞书", "聊天", "进行中"],
    missionSubtitle: "轻量问题只做即时回复，不触发文档和画布重绘，保持工作区安静和高效。",
    confidence: "96%",
    contextQuality: "高",
    workflow: [
      { id: "1", title: "分析消息上下文", status: "completed" },
      { id: "2", title: "判断当前意图", status: "completed" },
      { id: "3", title: "按需检索知识库", status: "completed" },
      { id: "4", title: "生成回复 / 文档", status: "running" },
      { id: "5", title: "同步到 Bitable", status: "pending" },
      { id: "6", title: "回传飞书群", status: "pending" },
    ],
    outputTabs: commonTabs,
    defaultTab: "chat",
    chatReply: {
      title: "聊天回复",
      body: "今天下午 3:30 在产品组飞书会议室，建议仅安排 20 分钟。我会在 3:25 再同步一次提醒。",
      source: "来源：飞书即时消息上下文 · 09:13",
    },
    document: {
      title: "会议纪要与方案预览",
      date: "2024 年 5 月 6 日 - 5 月 12 日",
      sections: [
        {
          title: "摘要",
          body:
            "基于本次会前确认与讨论，当前重点是统一会议时间、设备准备与演示议程，确保团队在正式彩排前完成关键项确认。",
        },
      ],
    },
    canvas: {
      title: "汇报画布预览",
      nodes: [
        { id: "n1", index: 1, title: "会议背景", bullets: ["确认演示时间", "统一参会节奏", "避免彩排冲突"], icon: "trend" },
        { id: "n2", index: 2, title: "关键结论", bullets: ["3:30 开始", "20 分钟", "会前二次提醒"], icon: "rocket" },
        { id: "n3", index: 3, title: "准备事项", bullets: ["设备检查", "议程确认", "人员到位"], icon: "calendar" },
        { id: "n4", index: 4, title: "风险提示", bullets: ["时间冲突", "设备异常", "信息遗漏"], icon: "alert" },
        { id: "n5", index: 5, title: "应对策略", bullets: ["提前提醒", "预留替代方案", "确认责任人"], icon: "spark" },
        { id: "n6", index: 6, title: "下一步", bullets: ["会后整理纪要", "补充方案", "输出 PPT"], icon: "check" },
      ],
    },
    disabledCards: [
      { title: "文档区域", subtitle: "当前聊天模式未刷新" },
      { title: "画布区域", subtitle: "当前聊天模式未刷新" },
    ],
    contextSources: [
      { id: "c1", title: "即时消息上下文", description: "最近 5 轮群聊与会议确认信息已读取。", status: "completed" },
      { id: "c2", title: "知识库检索", description: "已载入会议提醒模板与基础执行清单。", status: "completed" },
      { id: "c3", title: "多维表格进度", description: "当前尚未触发正式同步动作。", status: "pending" },
    ],
    sourceEvidence: [{ id: "e1", title: "飞书聊天记录", description: "会议时间确认与设置准备讨论。", tone: "chat" }],
    syncActions: [
      { id: "s1", title: "同步到 Bitable", status: "pending" },
      { id: "s2", title: "发送到飞书群", status: "running" },
      { id: "s3", title: "生成待办", status: "pending" },
    ],
    statusBadges: topBadges,
    systemNote: "当前使用 mock 数据支持演示，后续可接飞书 API、Bitable API 与 WebSocket 状态流。",
    actionButtons: ["分享", "导出"],
  },
  "weekly-marketing-summary": {
    id: "weekly-marketing-summary",
    layoutVariant: "doc",
    title: "每周营销总结",
    breadcrumb: ["Eko", "会话", "每周营销总结"],
    topBadges,
    navItems,
    assistantName: "Sarah Chen",
    assistantEmail: "在线",
    conversationTitle: "对话",
    messages: [
      {
        id: "d1",
        author: "Sarah Chen",
        role: "member",
        time: "9:02",
        body:
          "Hi Eko，帮我整理本周的营销复盘。包括各渠道活动表现、关键指标、预算消耗情况，并生成一份汇报文稿。最后同步到飞书营销群，方便团队查看。",
        avatar: "S",
      },
      {
        id: "d2",
        author: "Eko",
        role: "eko",
        time: "9:03",
        body: "好的，我将从以下来源获取数据并整理：\n\n• 活动数据看板\n• 渠道投放报告\n• 线索与转化数据\n\n完成后生成文稿并同步到飞书。",
        avatar: "E",
        helperText: "正在检索 5 个数据源...",
      },
      {
        id: "d3",
        author: "Eko",
        role: "eko",
        time: "9:04",
        body: "数据已准备就绪。我已生成初稿，包含摘要、关键亮点、活动表现和下周建议。文稿已生成在「每周营销总结」，请查看并告知是否需要调整。",
        avatar: "E",
        fileCard: {
          title: "每周营销总结（初稿）",
          typeLabel: "文稿",
          statusLabel: "已生成",
        },
      },
      {
        id: "d4",
        author: "Sarah Chen",
        role: "member",
        time: "9:05",
        body: "整体不错！请补充渠道 ROI 对比，并在活动表现部分增加转化漏斗数据。",
        avatar: "S",
      },
    ],
    missionTitle: "每周营销总结",
    missionBadges: ["飞书", "文稿", "进行中"],
    missionSubtitle:
      "将飞书群聊与 Bitable 渠道数据沉淀为周报文稿，支持一键同步营销群与多维表格，便于团队复盘与迭代。",
    confidence: "91%",
    contextQuality: "高",
    workflow: [
      { id: "1", title: "理解意图", status: "completed" },
      { id: "2", title: "路由输出", status: "completed" },
      { id: "3", title: "生成草稿", status: "running" },
      { id: "4", title: "同步结果", status: "pending" },
    ],
    workflowCards: [
      { id: "w1", title: "理解意图", status: "completed", timestamp: "9:02", subtitle: "已完成" },
      { id: "w2", title: "路由输出", status: "completed", timestamp: "9:03", subtitle: "文稿", tag: "文稿" },
      { id: "w3", title: "生成草稿", status: "running", timestamp: "9:04", subtitle: "进行中" },
      { id: "w4", title: "同步结果", status: "pending", subtitle: "待同步" },
    ],
    progress: 68,
    outputTabs: commonTabs,
    defaultTab: "doc",
    chatReply: {
      title: "聊天回复",
      body:
        "我已根据本周各渠道投放与线索转化数据整理出《每周营销总结》草案：含摘要、关键亮点、活动表现表与 ROI 对比，可在「文稿」页继续精修并同步到飞书营销群。",
      source: "来源：飞书营销群上下文 · 09:04",
    },
    document: {
      title: "每周营销总结",
      date: "2024 年 5 月 6 日 - 5 月 12 日",
      sections: [
        {
          title: "摘要",
          body:
            "本周整体营销投放保持提升，核心活动带来显著的线索增长与转化提升，预算使用效率优化。建议重点优化渠道 ROI 表现，并持续优化投放结构，聚焦高质量线索获取。",
        },
        {
          title: "关键亮点",
          bullets: [
            "总访问量 48.7 万，环比增长 18.6%，线索数 8,726，环比增长 24.3%；",
            "整体转化率 2.11%，较上周提升 0.34 个百分点；",
            "整体 ROI 1.321，付费投放渠道 ROI 表现最佳。",
          ],
        },
        {
          title: "活动表现",
          body: "以下为本周核心活动的数据表现：",
        },
      ],
      tableRows: [
        {
          campaign: "新品发布会直播",
          channel: "线上直播（抖音）",
          visits: "128,632",
          leads: "2,346",
          conversion: "1.82%",
          roi: "2.68",
          budget: "¥56,300",
        },
        {
          campaign: "母亲节促销活动",
          channel: "信息流广告（巨量）",
          visits: "182,745",
          leads: "4,128",
          conversion: "2.26%",
          roi: "3.52",
          budget: "¥78,600",
        },
        {
          campaign: "行业白皮书下载",
          channel: "内容运营（微信公众号）",
          visits: "96,412",
          leads: "1,862",
          conversion: "1.74%",
          roi: "2.31",
          budget: "¥21,400",
        },
        {
          campaign: "合作伙伴联合活动",
          channel: "企业微信 + EDM",
          visits: "120,883",
          leads: "1,934",
          conversion: "1.60%",
          roi: "2.12",
          budget: "¥18,900",
        },
      ],
    },
    canvas: {
      title: "营销画布预览（可选故事线）",
      nodes: [
        { id: "cn1", index: 1, title: "复盘范围", bullets: ["本周投放周期", "渠道覆盖", "预算口径"], icon: "trend" },
        { id: "cn2", index: 2, title: "渠道表现", bullets: ["信息流 / 搜索", "直播短视频", "私域转化"], icon: "rocket" },
        { id: "cn3", index: 3, title: "ROI 对比", bullets: ["同比上周", "Top 渠道", "低效关停"], icon: "calendar" },
        { id: "cn4", index: 4, title: "线索与漏斗", bullets: ["MQL→SQL", "表单质量", "销售跟进 SLA"], icon: "spark" },
        { id: "cn5", index: 5, title: "风险与阻塞", bullets: ["素材枯竭", "账户波动", "落地页跳转"], icon: "alert" },
        { id: "cn6", index: 6, title: "下周动作", bullets: ["预算倾斜", "A/B 文案", "复盘会议"], icon: "check" },
      ],
    },
    disabledCards: [
      { title: "聊天区域", subtitle: "当前处于文稿模式" },
      { title: "画布区域", subtitle: "可切换查看汇报结构" },
    ],
    contextSources: [
      { id: "cs1", title: "飞书营销数据看板", description: "", status: "completed" },
      { id: "cs2", title: "渠道投放报告（5.6 - 5.12）", description: "", status: "completed" },
      { id: "cs3", title: "线索与转化数据表", description: "", status: "completed" },
    ],
    sourceEvidence: [
      { id: "se1", title: "营销活动规划表 Q2", description: "更新于 5 月 10 日", tone: "document" },
      { id: "se2", title: "渠道投放复盘 5 月第 2 周", description: "更新于 5 月 11 日", tone: "document" },
      { id: "se3", title: "内容营销周报 5.6 - 5.12", description: "更新于 5 月 12 日", tone: "record" },
    ],
    syncActions: [
      { id: "sa1", title: "同步到多维表格", status: "completed" },
      { id: "sa2", title: "发送到飞书营销群", status: "completed" },
      { id: "sa3", title: "记录活动日志", status: "completed" },
    ],
    statusBadges: topBadges,
    systemNote: "当前使用 mock 数据支持演示，后续可替换为真实飞书 API、Bitable API 与 WebSocket 状态流。",
    actionButtons: ["分享", "导出", "同步"],
    relatedFiles: [
      { id: "rf1", title: "营销活动规划表 Q2", updatedAt: "更新于 5 月 10 日", tone: "doc" },
      { id: "rf2", title: "渠道投放复盘 5 月第 2 周", updatedAt: "更新于 5 月 11 日", tone: "doc" },
      { id: "rf3", title: "内容营销周报 5.6 - 5.12", updatedAt: "更新于 5 月 12 日", tone: "deck" },
    ],
    memoryNote: {
      title: "AI 记忆与上下文",
      body: "记住你的偏好、过往项目和常用口径，让 Eko 输出更贴合你的工作习惯。",
      action: "查看记忆",
    },
    syncOverview: {
      statusLabel: "已同步",
      items: ["最近同步：2 分钟前", "已同步至：飞书营销群"],
    },
    activities: [
      { id: "a1", title: "文稿已生成", time: "2 分钟前", tone: "doc" },
      { id: "a2", title: "路由为文稿模式", time: "3 分钟前", tone: "route" },
      { id: "a3", title: "数据源连接成功", time: "3 分钟前", tone: "data" },
      { id: "a4", title: "会话已开始", time: "4 分钟前", tone: "session" },
    ],
  },
  "q2-ads-review": {
    id: "q2-ads-review",
    layoutVariant: "canvas",
    title: "Q2 广告投放复盘",
    breadcrumb: ["Eko", "会话", "Q2 广告投放复盘"],
    topBadges,
    navItems,
    assistantName: "Sarah Chen",
    assistantEmail: "在线",
    conversationTitle: "对话",
    messages: [
      {
        id: "c1",
        author: "Leo",
        role: "member",
        time: "11:06",
        body: "Q2 投放要汇报，帮我把各渠道消耗、转化和 ROI 拉成一条能讲清楚的故事线。",
        avatar: "L",
      },
      {
        id: "c2",
        author: "Leo",
        role: "member",
        time: "11:07",
        mention: "@Eko",
        body: "按「为什么做—我们怎么投—结果与风险—下一步」来排画布，每块能对应到 Bitable 里的分渠道行。",
        avatar: "L",
      },
      {
        id: "c3",
        author: "Eko",
        role: "eko",
        time: "11:08",
        body: "已切到画布模式：我会把 Q2 群聊与投放表里的信息，整理成可汇报的 Canvas 分镜，并标出需你拍板的关键数字。",
        avatar: "E",
        actionCard: {
          title: "已进入工作台处理",
          description: "你可以直接打开工作台查看进度，并在确认后同步保存当前画布结构。",
          buttons: [
            { label: "打开工作台", tone: "primary" },
            { label: "查看进度" },
            { label: "确认保存", tone: "success" },
          ],
        },
      },
      {
        id: "c4",
        author: "Mia",
        role: "member",
        time: "11:10",
        body: "这个结构挺清楚，帮我补一下风险提醒和下一步计划。",
        avatar: "M",
      },
    ],
    missionTitle: "Q2 投放汇报画布",
    missionBadges: ["飞书", "画布", "进行中"],
    missionSubtitle:
      "将 Q2 各渠道投放、成本与转化从群聊 + 多维表格 + 知识库合成为可汇报的视觉故事线，支持确认后回写 Bitable。",
    confidence: "88%",
    contextQuality: "中等",
    workflow: [
      { id: "1", title: "分析 IM 上下文", status: "completed" },
      { id: "2", title: "判断当前意图", status: "completed" },
      { id: "3", title: "按需检索 RAG", status: "completed" },
      { id: "4", title: "生成回复 / 文稿", status: "running" },
      { id: "5", title: "同步到 Bitable", status: "warning" },
      { id: "6", title: "回传飞书群", status: "pending" },
    ],
    workflowCards: [
      { id: "cw1", title: "分析 IM 上下文", status: "completed", subtitle: "已完成" },
      { id: "cw2", title: "判断当前意图", status: "completed", subtitle: "已完成" },
      { id: "cw3", title: "按需检索 RAG", status: "completed", subtitle: "已完成" },
      { id: "cw4", title: "生成回复 / 文稿", status: "running", subtitle: "进行中" },
      { id: "cw5", title: "同步到 Bitable", status: "warning", subtitle: "预警" },
      { id: "cw6", title: "回传飞书群", status: "pending", subtitle: "待处理" },
    ],
    progress: 76,
    outputTabs: commonTabs,
    defaultTab: "canvas",
    chatReply: {
      title: "聊天回复",
      body: "当前为 Q2 投放复盘画布：侧栏可看到三源同步状态，主区可切换「聊天 / 文稿 / 画布」；确认结构后点操作卡中的「确认保存」可模拟归档。",
      source: "来源：飞书群聊 + 投放 Bitable 表 · 11:08",
    },
    document: {
      title: "Q2 广告投放复盘",
      date: "2025 年 Q2 · 草稿输入",
      sections: [
        {
          title: "摘要",
          body:
            "画布模式下，本节文稿作为结构化输入：汇总搜索/信息流/直播等分渠道花费、转化与 ROI，对齐 Bitable 行项目，便于生成画布分镜。",
        },
      ],
    },
    canvas: {
      title: "Q2 投放汇报画布",
      nodes: [
        { id: "can1", index: 1, title: "复盘背景与目标", bullets: ["Q2 预算口径", "核心 KPI", "对齐业务目标"], icon: "trend" },
        { id: "can2", index: 2, title: "分渠道拆解", bullets: ["搜索 vs 信息流", "直播短视频", "私域与裂变"], icon: "rocket" },
        { id: "can3", index: 3, title: "花费与 ROI", bullets: ["CAC / CPA", "环比变化", "异常账户"], icon: "calendar" },
        { id: "can4", index: 4, title: "素材与承接", bullets: ["创意衰减", "落地页转化", "质检结论"], icon: "spark" },
        { id: "can5", index: 5, title: "风险与对策", bullets: ["预算漂移", "账户关停", "备用素材池"], icon: "alert" },
        { id: "can6", index: 6, title: "Q3 动作与同步", bullets: ["预算迁移", "飞书归档", "Bitable 更新"], icon: "check" },
      ],
    },
    disabledCards: [
      { title: "聊天区域", subtitle: "聊天结论已沉淀为画布结构" },
      { title: "文稿区域", subtitle: "文稿摘要已被用于生成当前画布" },
    ],
    contextSources: [
      { id: "cc1", title: "即时消息上下文", description: "已识别来自群主的汇报画布请求。", status: "completed" },
      { id: "cc2", title: "知识库检索", description: "已载入文档摘要与演示结构提示。", status: "completed" },
      { id: "cc3", title: "多维表格进度", description: "导出元数据与负责人映射仍待处理。", status: "warning" },
    ],
    sourceEvidence: [
      { id: "ce1", title: "飞书聊天记录", description: "已识别将方案转为可汇报故事线的需求。", tone: "chat" },
      { id: "ce2", title: "知识库文档", description: "已载入演示结构指南与示例内容。", tone: "document" },
      { id: "ce3", title: "Bitable 记录", description: "审批通过后再执行画布同步。", tone: "record" },
    ],
    syncActions: [
      { id: "ca1", title: "同步到 Bitable", status: "warning" },
      { id: "ca2", title: "发送到飞书群", status: "pending" },
      { id: "ca3", title: "生成待办", status: "running" },
    ],
    statusBadges: topBadges,
    systemNote: "当前使用本地 mock 数据支持演示，后续可替换为真实 Feishu API、Bitable API 和 WebSocket 状态流。",
    actionButtons: ["分享", "导出"],
  },
};

export const sessionDetailData = sessionDetailDataMap["meeting-confirmation"];

export function getSessionDetailData(id: string): SessionDetailData {
  return sessionDetailDataMap[id] ?? sessionDetailDataMap["meeting-confirmation"];
}
