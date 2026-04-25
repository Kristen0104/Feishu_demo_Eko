# Eko 多端协同框架说明（MULTI_DEVICE_SYNC_SPEC.md）

> 目标：构建一套能在移动端和桌面端之间实时同步状态与数据的前端框架，让一端操作能无缝体现在另一端。

---

## 1. 多端协同目标

Eko 的多端协同不是简单响应式页面，而是 **同一个 Session 的状态在多个端之间实时一致**。

用户可能在以下场景中切换：

1. 在飞书群内 @Eko 触发任务。
2. 在 PC 端打开 Eko Workspace 查看完整画布。
3. 在手机端打开同一链接查看进度或输入微调指令。
4. AI 正在生成时，所有端都看到相同进度。
5. 创建者点击确认保存后，所有端看到 Bitable 已归档状态。

---

## 2. 多端角色设计

| 角色 | 权限 | UI 表现 |
|---|---|---|
| Creator 创建者 | 可编辑、可输入指令、可确认保存 | 显示输入框和操作按钮 |
| Viewer 观摩者 | 只读查看 | 隐藏输入框，只展示实时进度 |
| Agent 系统 | 执行任务、锁定状态、广播更新 | 显示状态机和进度 |

---

## 3. 需要同步的状态

### 3.1 Agent 状态

```ts
type AgentState =
  | "IDLE"
  | "ANALYZING"
  | "RETRIEVING"
  | "GENERATING"
  | "SYNCING"
  | "COMPLETED"
  | "ERROR";
```

### 3.2 Surface 状态

```ts
type SurfaceType = "chat" | "document" | "canvas";
```

### 3.3 Session 状态

```ts
type WorkspaceSessionState = {
  sessionId: string;
  activeSurface: SurfaceType;
  agentState: AgentState;
  progress: number;
  lockStatus: "locked" | "unlocked";
  role: "creator" | "viewer";
  documentVersion: number;
  canvasVersion: number;
  selectedSlideId?: string;
  bitableSyncStatus: "idle" | "syncing" | "synced" | "error";
  lastSyncedAt?: string;
};
```

---

## 4. 推荐 WebSocket / SSE 事件

MVP 可以先用 mock，后续接真实 WebSocket 或 SSE。

```ts
type SyncEvent =
  | {
      type: "agent.state.changed";
      sessionId: string;
      state: AgentState;
      progress: number;
    }
  | {
      type: "surface.changed";
      sessionId: string;
      surface: SurfaceType;
    }
  | {
      type: "document.updated";
      sessionId: string;
      markdown: string;
      version: number;
    }
  | {
      type: "canvas.updated";
      sessionId: string;
      canvasJson: unknown;
      version: number;
    }
  | {
      type: "slide.selected";
      sessionId: string;
      slideId: string;
    }
  | {
      type: "bitable.synced";
      sessionId: string;
      recordUrl: string;
    }
  | {
      type: "workspace.locked" | "workspace.unlocked";
      sessionId: string;
      reason?: string;
    };
```

---

## 5. 前端状态管理建议

建议使用 Zustand 管理工作台状态。

### store 结构建议

```ts
type WorkspaceStore = {
  session: WorkspaceSessionState | null;
  setSession: (session: WorkspaceSessionState) => void;
  applySyncEvent: (event: SyncEvent) => void;
  setActiveSurface: (surface: SurfaceType) => void;
  setAgentState: (state: AgentState, progress?: number) => void;
};
```

### 为什么用 Zustand

- 轻量；
- 适合跨组件共享状态；
- 比 Context 更适合频繁更新；
- 方便后续接 WebSocket event。

---

## 6. 桌面端与移动端 UI 差异

### 桌面端

桌面端是主创作画布：

- 三栏工作台；
- 完整 Mission Control；
- Document Preview；
- Tldraw / Canvas；
- Context & Sync 面板；
- Bitable 操作按钮。

### 移动端

移动端是轻量控制器：

- 当前任务状态；
- Agent progress；
- 当前 Surface；
- 确认 / 取消 / 保存；
- 简单指令输入；
- PPT 翻页；
- 只读观摩模式。

---

## 7. MVP 实现路线

### Phase 1：Mock 同步

- 用 Zustand 存状态。
- 用按钮模拟状态变化。
- 在桌面端和移动端页面共享 mock state。
- 使用 query 参数模拟同一个 session：

```text
/workspace?sessionId=demo-001
/mobile?sessionId=demo-001
```

### Phase 2：接入后端状态轮询

- 前端每 1–2 秒请求一次 `/sessions/{id}/state`。
- 后端返回当前状态。
- 用于在 WebSocket 未完成前保证演示可用。

### Phase 3：接入 WebSocket / SSE

- 前端建立连接。
- 后端推送 Agent 状态、文档更新、Canvas 更新。
- 前端通过 `applySyncEvent()` 更新 store。

### Phase 4：冲突与锁定

- AI 生成中进入 `locked`。
- 创建者输入框禁用。
- Viewer 始终只读。
- 断线后显示 Reconnecting。
- 重连后拉取最新 snapshot。

---

## 8. 多端同步验收标准

- [ ] PC 端切换 Document / Canvas，移动端同步更新当前 Surface。
- [ ] Agent 状态从 ANALYZING 到 COMPLETED，两个端显示一致。
- [ ] AI 生成时，所有端显示 locked 状态。
- [ ] 移动端点击下一页，桌面端 Canvas 当前页同步变化。
- [ ] 创建者点击确认保存，移动端和桌面端都显示 Bitable 已同步。
- [ ] Viewer 只读，不展示指令输入框。
- [ ] WebSocket Pending 时，页面仍可通过 Mock Mode 演示。
