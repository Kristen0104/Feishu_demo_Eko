# Eko 技术架构文档

**产品名称**：Eko  
**版本**：v1.0  
**日期**：2026-04-24

---

## 1. 总体架构

Eko 采用 **飞书入口 + FastAPI 接入层 + Agent 编排层 + RAG / Bitable 知识层 + Redis 实时总线 + PostgreSQL 持久化层** 的全栈架构。

```text
飞书群 / 飞书卡片 / Web 工作台
        |
        v
Next.js 前端工作台
        |
        v
FastAPI 接入层
   - Auth / Session / Agent / RAG / Bitable / Feishu / Sync / Team
        |
        v
Agent 编排层
   - RouterAgent
   - PlannerAgent
   - AgentRuntime (LangGraph)
   - Tool Registry
        |
        +------------------------------+
        |                              |
        v                              v
RAG / Bitable 上下文层         文档 / PPT / 画板执行层
        |                              |
        +--------------+---------------+
                       v
             Redis 实时总线与会话同步
                       |
                       v
                PostgreSQL + pgvector
```

Agent 的执行链路为：

```text
context -> retrieval -> planner -> tool_execute
```

---

## 2. 前端层

### 2.1 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| UI 框架 | Next.js 16 + React 19 | 工作台主界面 |
| 状态管理 | Zustand | 会话状态、用户状态、实时数据 |
| 画布 | tldraw | 画板与 PPT 相关编辑体验 |
| 动效 | Framer Motion | 轻量交互动效 |

### 2.2 页面范围

- 登录与飞书绑定
- 会话列表与会话详情
- 知识库与 Bitable 数据源管理
- 文档、画板、PPT 工作区
- 团队和设置页面
- 个人中心页面

---

## 3. 后端层

### 3.1 主要模块

| 模块 | 作用 |
|------|------|
| Auth | 飞书登录、账号绑定、JWT 鉴权 |
| Agent | 意图路由、规划、执行、流式事件 |
| RAG | 文件入库、Embedding、pgvector 检索 |
| Bitable | 结构化数据发现、查询、归档 |
| Feishu | 卡片、画板、文档同步、事件回调 |
| Sync | 会话列表、上下文选择、WebSocket 同步 |
| Team | 成员邀请与会话协作 |
| Document / Canvas / AIPPT | 文档、画板、AI PPT 产出 |

### 3.2 Agent 编排

`RouterAgent` 负责判断用户是 `chat`、`docx`、`ppt` 还是 `board`。  
`AgentRuntime` 负责把一轮任务拆成：

1. 装载上下文
2. 检索知识和结构化数据
3. 生成可执行计划
4. 按计划调用工具

`PlannerAgent` 负责将自然语言任务转成 JSON 计划。  
`Tool Registry` 则保存可调用工具的规范与输入 schema。

---

## 4. 知识与数据层

### 4.1 RAG

- 文件入库支持文本解析、分片和 Embedding。
- 检索时使用 pgvector cosine distance。
- 当前没有独立 reranker 模型。
- Agent 链路中默认取 RAG Top-4，再与 Bitable Top-4 合并后保留最多 8 条上下文。

### 4.2 Bitable

- Bitable 同时承担结构化上下文和产物归档的角色。
- 查询失败不会阻断主任务。
- 支持数据源发现、字段检查、表/视图浏览和归档。

---

## 5. Redis 实时总线

Redis 负责：

- Agent 状态广播
- Session 状态同步
- 飞书同步结果推送
- 实时 WebSocket / SSE 数据转发
- 部分队列与缓存能力

它不是纯缓存层，而是系统内的实时协同骨架。

---

## 6. 存储层

### 6.1 PostgreSQL

- 用户、会话、团队、协作邀请、数据源配置、归档记录等关系数据。

### 6.2 pgvector

- 存储 RAG 向量块。
- 通过向量相似度做检索排序。

### 6.3 JSON / 文本产物

- 会话上下文
- 画板快照
- 任务计划
- 生成日志

---

## 7. 状态机

Agent 在单轮任务中会经历这些阶段：

```text
IDLE -> ANALYZING -> RETRIEVING -> PLANNING -> EXECUTING -> SYNCING -> COMPLETED
```

其中：

- `ANALYZING`：识别意图
- `RETRIEVING`：检索群聊、知识库、Bitable、当前产物
- `PLANNING`：生成计划
- `EXECUTING`：调用具体工具
- `SYNCING`：推送实时状态和结果

---

## 8. 部署

### 8.1 开发环境

- 前端：`npm run dev`
- 后端：`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- 基础依赖：PostgreSQL、Redis

### 8.2 生产环境

- 可采用多实例 FastAPI 部署
- PostgreSQL 主从或托管数据库
- Redis 高可用
- Feishu 应用凭证按环境隔离配置

---

## 相关文档

- [PRD.md](PRD.md)
- [API.md](API.md)
- [README.md](README.md)
