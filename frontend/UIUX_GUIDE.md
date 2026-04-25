# Eko 前端 UI/UX 设计指南（UIUX_GUIDE.md）

> 目标：做出科技感、简洁、清晰、适合忙碌用户快速理解的 AI Workplace 页面。

---

## 1. 设计关键词

Eko 的视觉方向建议定义为：

```text
清爽科技感 / 专业 SaaS / AI Workplace / 飞书式协作 / Slack 式信息流 / Notion 式文档 / Linear 式状态管理
```

不建议做：

- 过重的拟物风；
- 过多霓虹色；
- 复杂大动效；
- 信息密度过高；
- 一屏塞满开发状态。

---

## 2. 页面信息层级

### 一级信息

用户最关心：

1. 当前任务是什么？
2. AI 正在做什么？
3. 结果在哪里？
4. 下一步能点什么？

这些信息应该在首屏最明显位置。

### 二级信息

辅助判断：

- Intent；
- Confidence；
- Context Quality；
- RAG evidence；
- Bitable sync status。

### 三级信息

开发状态：

- Mock Mode；
- WebSocket Pending；
- API Contract Ready；
- Frontend MVP。

这些放底部或小 badge，不要抢主视觉。

---

## 3. 推荐布局

```text
┌────────────────────────────────────────────────────────────┐
│ Top Header                                                  │
├───────────────┬──────────────────────────────┬─────────────┤
│ IM Chat        │ Main Workspace                │ Context     │
│               │ Agent Mission Control         │ & Sync      │
│               │ Output Surface                │             │
└───────────────┴──────────────────────────────┴─────────────┘
```

比例建议：

```text
左侧 300–340px
中间 minmax(0, 1fr)
右侧 300–340px
```

移动端：

- 单列布局；
- 顶部显示当前任务；
- 下方显示进度和快捷操作；
- 内容预览折叠展示。

---

## 4. 组件视觉规则

### 4.1 Intent Badge

| Intent | 颜色 |
|---|---|
| CHAT | Green |
| DOC | Blue |
| CANVAS | Purple / Orange |

### 4.2 状态颜色

| 状态 | 颜色 |
|---|---|
| Completed | Green |
| Running | Blue / Purple |
| Pending | Gray |
| Warning | Amber |
| Error | Red |

### 4.3 卡片风格

建议：

- 白色或半透明白底；
- 轻边框；
- 24–32px 大圆角；
- 轻微 shadow；
- 大块留白；
- 标题清晰；
- badge 不要过多。

---

## 5. Busy User 体验原则

### 5.1 三秒理解

用户打开页面后，应在三秒内知道：

- 当前任务；
- 当前 intent；
- 当前进度；
- 当前输出。

### 5.2 一次只突出一个主操作

例如：

- 当前还没生成：主按钮是 `Start / Generate`；
- 已生成：主按钮是 `Sync to Bitable`；
- 已同步：主按钮是 `Send to Feishu Group`。

### 5.3 不打扰原则

CHAT intent 不刷新 Document / Canvas，不造成页面跳动。

### 5.4 可解释 AI

任何正式输出都应该展示：

- 用了哪些上下文；
- 哪些内容来自 RAG；
- 哪些内容来自 Bitable；
- 哪些是 AI 推断。

### 5.5 操作可恢复

用户需要知道：

- 能重新生成；
- 能查看 source；
- 能同步；
- 能取消或返回。

---

## 6. 当前页面优化建议

### 6.1 左侧

当前左侧如果以 Case A/B/C 为主，会更像 demo gallery。建议改为 IM Chat Panel：

- 主体展示消息流；
- 顶部用 Scenario Switcher 切换 Case；
- 底部保留输入框；
- Agent 回复在消息流内出现。

### 6.2 中间

把 Agent Mission Control 放到主区域顶部，强化 Pilot 感。

输出区域放在 Mission Control 下方，减少用户在左右两侧寻找结果的成本。

### 6.3 右侧

把 Status Panel 改成 Context & Sync Panel：

- Context Sources；
- Source Evidence；
- Sync Actions；
- System Status。

开发状态放底部。

---

## 7. 视觉参考

可以参考：

- 飞书：卡片、群聊、文档、多维表格闭环；
- Slack：消息流和 bot 交互；
- 钉钉：任务状态、卡片操作、工作流推进；
- Notion：文档预览；
- Linear：状态和 issue 风格；
- Miro / FigJam：画布视觉化。

---

## 8. 具体文案建议

### 顶部标题

```text
Eko Workspace
Turn IM discussions into documents, presentation canvas, and synced project records.
```

### 状态面板

```text
Context & Sync
Current Task
Context Sources
Source Evidence
Sync Actions
System Status
```

### 空状态

```text
等待 @Eko 指令
从飞书群聊或 Mock IM 中输入一句任务，Eko 会自动判断是即时回复、文档生成还是画布生成。
```

### 错误状态

```text
连接暂时不可用
当前已切换到 Mock Mode，仍可完成演示流程。
```

---

## 9. 动效建议

动效只用于帮助理解状态，不要炫技。

推荐：

- Agent step 逐条进入；
- Canvas card 轻微 stagger；
- Sync 成功时出现绿色 check；
- WebSocket pending 时轻微 pulse；
- AI generating 时按钮锁定并显示 loading。

不建议：

- 大面积页面抖动；
- 长时间 loading；
- 所有卡片都动画；
- 频繁闪烁。

---

## 10. 前端设计师与组员配合方式

作为前端设计师，需要主动对齐：

### 和后端

- API 返回字段；
- WebSocket event；
- Bitable sync status；
- 权限字段；
- 错误码。

### 和 Agent / Prompt

- intent 文案；
- 状态机步骤；
- source evidence；
- 缺失信息追问；
- demo case 文案。

### 和产品 / Demo

- 每个页面在 demo 中的讲法；
- 评委第一眼能不能看懂；
- 哪些功能是真实，哪些是 mock；
- 哪些按钮只是占位。

---

## 11. UI 优先级

### P0

- 三栏工作台清晰；
- CHAT / DOC / CANVAS 分流明显；
- Mission Control 清楚；
- Context & Sync 右侧可理解；
- 移动端基本可用。

### P1

- Source Evidence；
- Bitable Sync Action；
- Creator / Viewer 权限状态；
- Lock 状态；
- Agent step 动效。

### P2

- 深色模式；
- 高级 Tldraw 交互；
- 飞书卡片原生样式完全还原；
- 复杂多端冲突提示。
