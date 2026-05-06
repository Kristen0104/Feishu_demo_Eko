import type { SyncSession } from "@/lib/sync/live-session-list-data";

function isoMinutesAgo(minutesAgo: number): string {
  const d = new Date(Date.now() - minutesAgo * 60 * 1000);
  return d.toISOString();
}

/**
 * 展示用静态数据（前端 mock），用于无后端时演示会话列表/详情。
 * - 不依赖后端
 * - 可被 Next route handler 复用
 */
export const MOCK_SYNC_SESSIONS: SyncSession[] = [
  {
    session_id: "demo-chat",
    source: "feishu",
    title: "飞书闲聊：会议时间确认",
    summary:
      "今天下午 3:30 在产品组飞书会议室，建议仅安排 20 分钟。我会在 3:25 再同步一次提醒。",
    status: "进行中",
    opened_at: isoMinutesAgo(30),
    updated_at: isoMinutesAgo(2),
    context_size: 5,
    intent: "chat",
    messages: [
      {
        role: "user",
        content: "我们下午几点开会？",
        timestamp: Date.now() - 12 * 60 * 1000,
        platform_display_name: "Leo",
        mention: "@Eko",
      },
      {
        role: "assistant",
        content: "今天下午 3:30 在产品组飞书会议室，建议仅安排 20 分钟。我会在 3:25 再同步一次提醒。",
        timestamp: Date.now() - 11.6 * 60 * 1000,
        sent: true,
      },
      {
        role: "user",
        content: "收到，谢谢！",
        timestamp: Date.now() - 11.2 * 60 * 1000,
        platform_display_name: "Mia",
      },
    ],
    context_messages: [
      { role: "system", content: "来源：飞书群聊（mock）最近 5 条消息。", timestamp: Date.now() - 15 * 60 * 1000 },
    ],
  },
  {
    session_id: "demo-word",
    source: "feishu",
    title: "运营方案梳理（文档）",
    summary: `# 运营方案梳理（初稿）

## 一、背景与目标
- **背景**：讨论主要发生在飞书群，结论分散在多轮聊天中，产物需要快速沉淀与复用。
- **目标**：把刚才讨论的运营方案整理为可直接分享的文档结构，并补齐执行计划与时间节点。

## 二、核心策略
- **定位**：以“拉新 + 激活 + 转化”为主线，拆为 3 个阶段。
- **策略组合**：内容种草（模板复用）+ 触达转化（关键节点）+ 复盘沉淀（回流知识库）。

## 三、执行计划（含时间节点）
- **T+0（今天）**：整理群聊结论，生成初稿文档并同步到工作台。
- **T+1（明天）**：补齐负责人/里程碑/指标口径，完成二次迭代。
- **T+2（后天）**：将文档转为汇报 PPT 结构，导出 PPTX。

## 四、风险与对策
- **信息遗漏**：群聊上下文 + 知识库模板双源补齐。
- **口径不一致**：采用固定模板字段（目标/指标/里程碑/负责人）。
- **协作冲突**：创建者可编辑，其他成员只读观摩。

## 五、下一步
- 继续补齐“第二部分执行计划”的时间节点与负责人映射
- 需要时一键转 PPT，并导出 PPTX`,
    status: "已同步",
    opened_at: isoMinutesAgo(1440),
    updated_at: isoMinutesAgo(12),
    context_size: 50,
    intent: "doc",
    artifact: {
      kind: "docx",
      status: "completed",
      progress: 1,
      job_id: "demo-doc-job",
      download_url: null,
      current_step: "文档已生成（mock）",
      content: null,
    },
    messages: [
      {
        role: "user",
        content: "@Eko 帮我梳理一下刚才讨论的运营方案，结合知识库里的模板，写成文档。",
        timestamp: Date.now() - 8 * 60 * 1000,
        platform_display_name: "Leo",
      },
      {
        role: "assistant",
        content: "已识别为文档创作意图。我会拉取群聊最近讨论，并检索知识库里的运营方案模板。",
        timestamp: Date.now() - 7.6 * 60 * 1000,
        helperText: "正在分析意图...",
      },
      {
        role: "assistant",
        content: "资料已准备就绪：群聊上下文 + 模板 Top-5。正在生成文档初稿。",
        timestamp: Date.now() - 7.1 * 60 * 1000,
        helperText: "正在获取资料...",
      },
      {
        role: "assistant",
        content: "文档初稿已生成，你可以打开工作台查看并继续追加指令优化。",
        timestamp: Date.now() - 6.6 * 60 * 1000,
        fileCard: { title: "运营方案梳理（初稿）", typeLabel: "文稿", statusLabel: "已生成" },
        actionCard: {
          title: "已进入工作台处理",
          description: "创建者可编辑，其他成员只读观摩。",
          buttons: [
            { label: "打开工作台", tone: "primary" },
            { label: "查看进度" },
          ],
        },
      },
      {
        role: "user",
        content: "把第二部分的执行计划加上时间节点",
        timestamp: Date.now() - 5.2 * 60 * 1000,
        platform_display_name: "Leo",
      },
      {
        role: "assistant",
        content: "已补齐时间节点，并将执行计划拆成 T+0 / T+1 / T+2 三段。",
        timestamp: Date.now() - 4.8 * 60 * 1000,
        helperText: "GENERATING...",
      },
    ],
    context_messages: [
      { role: "system", content: "来源：飞书群聊最近 50 条（mock）。", timestamp: Date.now() - 60 * 60 * 1000 },
      { role: "system", content: "来源：知识库运营方案模板 Top-5（mock）。", timestamp: Date.now() - 59 * 60 * 60 * 1000 },
    ],
  },
  {
    session_id: "demo-canvas",
    source: "feishu",
    title: "方案汇报 PPT（画布）",
    summary: "文档已完成，切换到画布模式生成 PPT 结构，并支持导出与归档回流。",
    status: "进行中",
    opened_at: isoMinutesAgo(60),
    updated_at: isoMinutesAgo(3),
    context_size: 80,
    intent: "board",
    artifact: {
      kind: "ppt",
      intent: "board",
      status: "running",
      progress: 0.84,
      current_step: "PPT 结构已生成（mock）",
      job_id: "demo-ppt-job",
      download_url: null,
    },
    messages: [
      {
        role: "user",
        content: "把这个方案做成汇报 PPT",
        timestamp: Date.now() - 9 * 60 * 1000,
        platform_display_name: "Leo",
      },
      {
        role: "assistant",
        content: "收到。我会复用刚才的文档内容，自动切换到画布模式，生成 PPT 结构。",
        timestamp: Date.now() - 8.7 * 60 * 1000,
        helperText: "正在生成画布结构...",
      },
      {
        role: "assistant",
        content: "画布已生成：逻辑框架、执行计划、关键数据已可视化。你可以导出 PPTX 或确认保存归档。",
        timestamp: Date.now() - 8.2 * 60 * 1000,
        actionCard: {
          title: "画布已生成",
          description: "导出 PPTX / 确认保存后回流知识库（mock）。",
          buttons: [
            { label: "导出 PPTX", tone: "primary" },
            { label: "确认保存", tone: "success" },
          ],
        },
      },
      {
        role: "assistant",
        content: "提示：确认保存后，会话产物会回流到知识库，供下次创作直接复用。",
        timestamp: Date.now() - 7.8 * 60 * 1000,
      },
    ],
    context_messages: [
      { role: "system", content: "来源：飞书群聊讨论（mock）。", timestamp: Date.now() - 2 * 60 * 60 * 1000 },
      { role: "system", content: "来源：知识库过往运营方案模板（mock）。", timestamp: Date.now() - 48 * 60 * 60 * 1000 },
    ],
  },
];

export function findMockSyncSession(sessionId: string): SyncSession | null {
  const normalized = sessionId.trim();
  const alias = normalized === "demo-doc" ? "demo-word" : normalized === "demo-ppt" ? "demo-canvas" : normalized;
  return MOCK_SYNC_SESSIONS.find((s) => s.session_id === alias) ?? null;
}

