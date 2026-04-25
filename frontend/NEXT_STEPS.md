# Eko 前端下一步行动清单（NEXT_STEPS.md）

## 1. 当前判断

根据已上传文档和当前页面代码，前端已经完成了一个可演示的 MVP 框架：

- Next.js 页面可运行；
- 页面有 Header、左侧列表、中间 Mission Control、Output Surface、右侧 Status Panel；
- 可以基于 mock workspace 数据切换 Chat / Document / Canvas；
- Markdown 样式和浅色科技感背景已经有基础；
- Canvas 组件已使用 dynamic import，方向正确。

但现在还需要从“Case 展示页”升级为“真实 AI Workplace 工作台”。

---

## 2. 立即要做的 6 件事

### 任务 1：修复项目基础问题

- 删除损坏的 `src/app/favicon.ico`。
- 清理 `.next`。
- 确保 `npm run dev -- -p 3002` 可稳定运行。
- 检查页面无 build error。

### 任务 2：调整左侧结构

将 `CaseSidebar` 改造成：

```text
ChatPanel
├── ScenarioSwitcher
├── MessageList
├── AgentReply
└── MessageInput
```

目标：让页面更像飞书 / Slack 的 IM 工作流，而不是 Case Gallery。

### 任务 3：强化 Mission Control

在 `MissionControl` 中补充：

- Intent；
- Confidence；
- Context Quality；
- Agent State；
- Lock status；
- Workflow steps。

### 任务 4：重构右侧 StatusPanel

将 `StatusPanel` 改为 `ContextSyncPanel`：

```text
ContextSyncPanel
├── CurrentTaskCard
├── ContextSources
├── SourceEvidence
├── SyncActions
└── SystemStatus
```

目标：右侧从“开发状态面板”变成“上下文与同步操作面板”。

### 任务 5：新增移动端页面

新增：

```text
src/app/mobile/page.tsx
```

包含：

- 当前任务；
- Agent progress；
- 当前 surface；
- 快捷操作；
- 指令输入；
- Viewer / Creator 状态。

### 任务 6：定义同步类型

新增：

```text
src/types/sync.ts
```

包含：

- `WorkspaceSessionState`
- `SyncEvent`
- `AgentState`
- `SurfaceType`

为后续 WebSocket / Zustand 做准备。

---

## 3. 与后端对齐的接口

请和后端同学确认以下最小 API Contract：

```ts
type AgentExecuteResponse = {
  sessionId: string;
  taskId: string;
  intent: "CHAT" | "DOC" | "CANVAS";
  confidence: number;
  contextQuality?: number;
  agentState: "COMPLETED" | "ERROR" | "GENERATING";
  steps: {
    id: string;
    label: string;
    status: "completed" | "running" | "pending" | "error";
  }[];
  chatReply?: string;
  documentMarkdown?: string;
  canvasJson?: unknown;
  sourceEvidence?: {
    type: "im" | "rag" | "bitable" | "ai_inferred";
    title: string;
    content: string;
  }[];
  bitableSyncStatus?: "idle" | "syncing" | "synced" | "error";
};
```

---

## 4. 与 Agent / Prompt 同学对齐

需要让 Prompt 同学给前端固定这些内容：

- 三个 intent 的名称；
- 每个 intent 的触发例句；
- Agent steps 的中文文案；
- source evidence 格式；
- error / empty 文案；
- demo 讲解用例。

---

## 5. 前端开发顺序

建议按以下顺序完成：

```text
Day 1:
修复 favicon / dev server
整理当前组件结构
完成 ContextSyncPanel 静态版

Day 2:
改造左侧为 ChatPanel
强化 MissionControl
将 Case A/B/C 改成 ScenarioSwitcher

Day 3:
新增 mobile/page.tsx
定义 sync types
完成 Creator / Viewer / Lock UI 占位

Day 4:
接 mock API 或后端 /agent/execute
准备 demo 操作路径
```

---

## 6. 最终 Demo 前端路径

推荐演示顺序：

1. 飞书 / Mock IM 中输入 `@Eko` 指令。
2. 左侧消息流出现用户指令。
3. 中间 Mission Control 显示：
   - Intent；
   - Analyze；
   - Retrieve；
   - Generate；
   - Sync。
4. 中间输出区显示 Document 或 Canvas。
5. 右侧显示 RAG / Bitable / IM evidence。
6. 点击 Sync to Bitable。
7. 移动端页面同步显示 completed。
8. 说明 Mock Mode 可替换为真实 Feishu API。

---

## 7. 你作为前端负责人的工作重点

你现在最应该关注：

- 让页面一眼看起来像 workplace，而不是作业 demo；
- 让 Agent 工作流清楚；
- 让用户知道当前上下文来自哪里；
- 让多端同步有 UI 入口和状态；
- 让后端可以按固定 schema 接入；
- 不要过早纠结复杂动画和高保真视觉。
