# Eko 前端开发说明文档（Frontend.md）

> 适用阶段：2026.04.24–2026.04.27 前端架子搭建期  
> 目标：先把 Eko 的网页端工作台搭建清楚，并为后续 WebSocket、多端同步、Tldraw、FastAPI 和飞书卡片接入预留稳定接口。

---

## 1. 前端定位

Eko 前端不是普通的展示页面，而是一个 **AI Agent 工作台（Agent Workspace）**。

它的核心职责是：

1. 接收来自 IM / Mock IM / 飞书卡片链接的任务入口。
2. 展示 Agent 的任务理解、状态机和执行进度。
3. 根据 Agent 意图分流结果展示不同输出形态：
   - `CHAT`：即时回复，不触发文档或画布刷新。
   - `DOC`：Markdown / Word-like 文稿预览。
   - `PPT / CANVAS`：Tldraw / PPT-like 画布预览。
4. 展示三源上下文：
   - IM 群聊上下文；
   - 飞书 Bitable 项目数据；
   - RAG 知识库检索结果。
5. 支持移动端和桌面端共享同一 Session 状态。
6. 为后续飞书 Bitable 归档、卡片更新和知识库回流提供前端操作入口。

---

## 2. 当前前端已有基础

目前网页端已经具备一个可运行的工作台雏形：

- 使用 `Next.js App Router`。
- `layout.tsx` 中已经配置页面标题和描述。
- `globals.css` 中已经定义浅色科技感背景、字体体系、Markdown 样式。
- `page.tsx` 已经采用三栏工作台结构：
  - 左侧：Case / Scenario 列表；
  - 中间：Mission Control + Output Surface；
  - 右侧：Status Panel。
- 页面已经通过 `getWorkspaceData()` 加载 mock workspace 数据。
- Canvas 组件使用 dynamic import，避免 SSR 问题。
- 当前页面可以展示 Chat / Document / Canvas 三种 surface。

---

## 3. 当前前端需要调整的方向

当前页面更像 **Case Demo Gallery**，下一步需要升级成更真实的 **Workplace Workspace**。

建议改成以下信息架构：

```text
Top Header
├── 产品名 Eko Workspace
├── 当前模式：Mock Mode / Feishu Mode
├── 当前同步状态：WebSocket Pending / Connected
└── 当前身份：Creator / Viewer

Main Layout
├── 左侧：Feishu / Mock IM Chat Panel
├── 中间：Agent Mission Control + Output Surface
└── 右侧：Context & Sync Panel
```

---

## 4. 推荐页面结构

### 4.1 左侧：Feishu / Mock IM Chat Panel

左侧不建议继续主要展示 Case A / B / C 卡片，而应更像飞书 / Slack 的消息流。

应该包含：

- 当前群聊 / 项目房间名称；
- Mock IM 消息流；
- 用户 `@Eko` 指令；
- Agent 简短回复；
- 指令输入框；
- 三个 Scenario 快捷切换：
  - Chat Reply；
  - Document Preview；
  - Presentation Canvas。

建议组件名：

```text
components/chat/
├── ChatPanel.tsx
├── MessageList.tsx
├── MessageBubble.tsx
├── MessageInput.tsx
└── ScenarioSwitcher.tsx
```

---

### 4.2 中间：Agent Mission Control

中间是 Eko 的核心区域，必须让用户看清楚 Agent 正在做什么。

应该包含：

- 当前意图：`CHAT / DOC / CANVAS`
- 置信度：`confidence`
- 上下文质量：`contextQuality`
- 当前状态机：
  - `IDLE`
  - `ANALYZING`
  - `RETRIEVING`
  - `GENERATING`
  - `SYNCING`
  - `COMPLETED`
  - `ERROR`
- Workflow steps：
  1. Analyze IM context
  2. Classify intent
  3. Retrieve RAG knowledge if needed
  4. Generate reply / document / canvas
  5. Sync to Bitable
  6. Reply to Feishu group

建议组件名：

```text
components/agent/
├── MissionControl.tsx
├── AgentStepCard.tsx
├── IntentBadge.tsx
├── ContextQualityBar.tsx
└── AgentLockBanner.tsx
```

---

### 4.3 中间下方：Output Surface

根据 intent 显示不同输出。

#### CHAT

只显示即时回复，不刷新 Document / Canvas。

应该明确显示：

```text
No document or canvas generated.
```

#### DOC

显示 Markdown / Word-like 文稿预览。

应该包含：

- 标题；
- Markdown 正文；
- source tags；
- 生成按钮：
  - Regenerate；
  - Generate Canvas；
  - Sync to Bitable。

#### CANVAS

显示 PPT-like / Tldraw canvas。

MVP 可以先用卡片模拟 canvas，后续再接 Tldraw SDK。

建议组件名：

```text
components/surface/
├── OutputSurface.tsx
├── ChatReplySurface.tsx
├── DocumentSurface.tsx
├── CanvasSurface.tsx
├── SlideCard.tsx
└── SourceTags.tsx
```

---

### 4.4 右侧：Context & Sync Panel

右侧不建议主要展示开发状态。它应该承担真实 workplace 中的上下文和操作面板角色。

建议结构：

```text
Context & Sync
├── Current Task
├── Context Sources
├── Source Evidence
├── Sync Actions
└── System Status
```

#### Current Task

展示：

- Intent；
- Task title；
- Status；
- Confidence；
- Context Quality。

#### Context Sources

展示 Agent 使用了哪些上下文：

- IM Context：多少条消息；
- RAG Knowledge：命中了哪些文档；
- Bitable Progress：读取了多少任务；
- Previous Output：是否复用历史结果。

#### Source Evidence

展示生成依据：

- Feishu Chat；
- RAG Document；
- Bitable Record；
- AI Inferred。

#### Sync Actions

按钮：

- Sync to Bitable；
- Send to Feishu Group；
- Generate To-do；
- Export Preview。

#### System Status

开发状态放到底部：

- MVP Ready；
- Mock Mode；
- WebSocket Pending；
- API Contract Ready。

建议组件名：

```text
components/context/
├── ContextSyncPanel.tsx
├── CurrentTaskCard.tsx
├── ContextSources.tsx
├── SourceEvidence.tsx
├── SyncActions.tsx
└── SystemStatus.tsx
```

---

## 5. 多端协同框架前端职责

多端协同不是简单“响应式布局”，而是同一 Session 状态在不同端实时一致。

前端需要维护以下状态：

```ts
type WorkspaceSessionState = {
  sessionId: string;
  mode: "mock" | "feishu";
  role: "creator" | "viewer";
  lockStatus: "unlocked" | "locked";
  agentState:
    | "IDLE"
    | "ANALYZING"
    | "RETRIEVING"
    | "GENERATING"
    | "SYNCING"
    | "COMPLETED"
    | "ERROR";
  activeSurface: "chat" | "document" | "canvas";
  activeCanvasVersion: number;
  activeDocumentVersion: number;
  selectedSlideId?: string;
  progress: number;
  lastSyncedAt?: string;
};
```

前端需要支持：

1. PC 端打开卡片后进入完整工作台。
2. 移动端打开卡片后进入轻量控制台。
3. 创建者可编辑，其他成员只读观摩。
4. AI 生成时输入框自动锁定。
5. 一端切换 surface、翻页、确认保存，另一端同步更新。
6. WebSocket 未接入前，先用 mock state 和 UI 状态占位。

---

## 6. 推荐前端目录结构

```text
src/
├── app/
│   ├── page.tsx
│   ├── mobile/
│   │   └── page.tsx
│   └── layout.tsx
├── components/
│   ├── chat/
│   ├── agent/
│   ├── surface/
│   ├── context/
│   ├── sync/
│   └── shared/
├── lib/
│   ├── adapters/
│   ├── services/
│   ├── mocks/
│   ├── store/
│   └── utils/
├── types/
│   ├── workspace.ts
│   ├── sync.ts
│   ├── agent.ts
│   └── surface.ts
└── styles/
```

---

## 7. 当前阶段前端验收标准

### 4.24–4.27 必须完成

- [ ] Next.js 项目可以稳定启动。
- [ ] 首页工作台三栏布局稳定。
- [ ] 左侧能展示 Mock IM 消息流。
- [ ] 能切换 Chat / Document / Canvas 三种场景。
- [ ] 中间 Mission Control 能展示 intent、steps、status。
- [ ] 右侧 Context & Sync 面板能展示上下文来源和同步动作。
- [ ] DOC 场景能展示 Markdown 文稿。
- [ ] CANVAS 场景能展示 PPT-like / Canvas mock。
- [ ] CHAT 场景不会触发文档或画布刷新。
- [ ] UI 具备科技感、简洁、清晰，适合忙碌用户快速理解。

### 4.27–5.3 继续完成

- [ ] 接入真实 `/agent/execute` 或 mock-compatible API。
- [ ] 接入 WebSocket / SSE 状态流。
- [ ] Zustand store 管理多端状态。
- [ ] 接入 Tldraw SDK。
- [ ] 接入 Bitable sync 状态。
- [ ] 完成移动端轻量控制台。

---

## 8. 前端与其他组员协作方式

### 与后端同学对齐

需要对齐：

1. `/agent/execute` 返回结构。
2. WebSocket 事件名称。
3. Session ID 和权限角色字段。
4. Canvas JSON / Document Markdown 数据结构。
5. Bitable 归档状态字段。

### 与 Agent / Prompt 同学对齐

需要对齐：

1. CHAT / DOC / CANVAS intent 的判定规则。
2. 每种 intent 的 UI 展示方式。
3. Agent 状态机步骤文案。
4. source evidence 格式。
5. 错误提示和空状态文案。

---

## 9. 前端设计原则

Eko 面向忙碌用户，因此页面必须满足：

1. **三秒看懂当前状态**  
   用户打开页面后，应立刻知道当前任务是什么、AI 做到哪一步、下一步能做什么。

2. **主任务优先**  
   中间主区域只展示 Agent 和输出结果，不要被开发状态、说明文字、过多标签干扰。

3. **少即是多**  
   忙碌用户不想读长说明。状态用 badge、progress、checkmark 表达。

4. **可控的 AI**  
   生成过程必须可见，用户知道 AI 用了哪些上下文，哪些内容已同步，哪些还待确认。

5. **不打扰原则**  
   CHAT intent 不刷新 canvas；创作 intent 才打开文档或画布。

6. **科技感来自秩序，不是炫技**  
   用清晰卡片、微动效、渐变背景、状态色建立专业感，不要堆复杂动画。

---

## 10. 下一步前端开发任务

建议你接下来按以下顺序推进：

1. 将左侧 `CaseSidebar` 改造成 `ChatPanel + ScenarioSwitcher`。
2. 将右侧 `StatusPanel` 改造成 `ContextSyncPanel`。
3. 强化中间 `MissionControl`，加入 intent、confidence、contextQuality、state machine。
4. 将 `Output Surface` 中的 Chat / Document / Canvas 三种状态组件化。
5. 新增 `mobile/page.tsx`，做移动端轻量控制台。
6. 定义 `WorkspaceSessionState` 和 `SyncEvent` 类型。
7. 与后端同学约定 `/agent/execute` 和 WebSocket event schema。
8. 再接真实 API，当前先保持 mock data 可演示。
