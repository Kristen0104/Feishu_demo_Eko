# Eko API 接口说明

**版本**：v1.2  
**日期**：2026-04-26  
**基础路径**：`/api/v1`

---

## 1. 总览

本文档描述当前后端骨架在 `/api/v1` 下暴露的接口。这里只保留目前代码里已经存在的路由和响应语义，暂不展开未实现的业务流程。占位接口会明确标注为框架预留。

### 1.1 通用约定

| 项目 | 说明 |
|------|------|
| 基础路径 | `/api/v1` |
| 鉴权头 | `Authorization: Bearer {token}` |
| 数据格式 | JSON |
| 通用包裹 | 大多数接口返回 `ApiResponse` |

### 1.2 通用响应包裹

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

---

## 2. 路由分组

当前后端骨架按以下分组组织：

- `auth`
- `canvas`
- `agent`
- `rag`
- `feishu`
- `ppt`
- `workspace`
- `sync`
- `system`

这些分组定义了当前重构后的框架级路由面，后续可以继续扩展业务，但不会改变这套基础分组。

---

## 3. 鉴权

### 鉴权说明

- 当前登录方式基于飞书认证。
- 受保护接口使用 Bearer Token 鉴权。
- 飞书 OAuth `state` 使用 Redis 一次性保存与消费。
- 本地用户、飞书账号和 OAuth token 使用 PostgreSQL 持久化。

### GET `/auth/feishu/login-url`

生成飞书 OAuth 授权 URL，并在 Redis 写入一次性 `state`。

**查询参数**

- `redirect_uri`：可选。测试页可传当前页面地址，后端默认使用配置里的飞书回调地址。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "authorize_url": "https://accounts.feishu.cn/open-apis/authen/v1/authorize?...",
    "state": "string",
    "expires_in": 600
  }
}
```

### GET `/auth/feishu/callback`

飞书 OAuth 回调入口，使用 `code + state` 完成登录并签发本系统 JWT。

**查询参数**

- `code`：飞书回调 code
- `state`：此前 `/auth/feishu/login-url` 返回的一次性 state
- `redirect_uri`：可选。需要与生成授权 URL 时的 redirect URI 保持一致。

### POST `/auth/feishu/login`

测试页使用飞书登录 `code + state` 换取本系统 JWT 和基础用户信息。该接口与 callback 共用登录服务逻辑，便于前端手动粘贴 code 联测。

**请求体**

```json
{
  "code": "string",
  "state": "string"
}
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "string",
    "expires_in": 3600,
    "user": {
      "user_id": "string",
      "display_name": "string",
      "feishu_user_id": "string"
    }
  }
}
```

### GET `/auth/me`

返回当前 Bearer Token 对应的登录用户信息。

**请求头**

- `Authorization: Bearer {access_token}`

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user_id": "string",
    "display_name": "string",
    "feishu_user_id": "string"
  }
}
```

### 登录相关存储

| 存储 | Key / 表 | 用途 |
|------|----------|------|
| Redis | `feishu:oauth:state:{state}` | OAuth state 一次性校验，过期后无法登录 |
| PostgreSQL | `users` | 本系统用户 |
| PostgreSQL | `feishu_accounts` | 飞书 open_id / union_id 与本地用户绑定 |
| PostgreSQL | `feishu_oauth_tokens` | 用户飞书 access token / refresh token，用于后续邀请好友等飞书 API |

---

## 4. Canvas

Canvas 是当前内容工作台的主框架术语。现在的路由只暴露按会话维度的画板元数据。

### GET `/canvas/sessions/{session_id}`

返回当前画板会话的 stub 信息。

**路径参数**

- `session_id`：画板会话标识

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "string",
    "title": "string",
    "mode": "string"
  }
}
```

---

## 5. Agent

当前 Agent 面是任务提交占位接口，仅保留异步任务入口，不描述尚未实现的执行细节。

### POST `/agent/tasks`

创建一个 Agent 任务。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "string",
    "status": "accepted"
  }
}
```

---

## 6. RAG

当前 RAG 面是文件列表占位接口，作为知识文件管理的框架预留入口。

### GET `/rag/files`

返回当前后端骨架可见的 RAG 文件列表。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "file_id": "string",
      "filename": "string",
      "source": "string"
    }
  ]
}
```

---

## 7. 飞书

飞书面当前只保留卡片元数据读取能力，属于后续平台集成的框架预留接口。

### GET `/feishu/cards/{card_id}`

返回一个飞书卡片 stub。

**路径参数**

- `card_id`：卡片标识

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "card_id": "string",
    "title": "string",
    "platform": "feishu"
  }
}
```

---

## 8. PPT

PPT 模块独立于 `canvas/board`。它以 JSON deck 作为中间层：生成、自然语言修改、HTML 预览和 PPTX 导出都围绕同一份 deck 数据工作，不复用飞书白板节点渲染流程。

试验版多布局 schema 已明确支持 slide 级 `layout` 字段，当前可用值为 `cover`、`bullets`、`two_column`、`timeline`、`metrics`、`summary`。这一版的目标是让前端联测和导出验证能直接看出结构差异，而不是把所有页面都压成同一种版式。

### 预期新增 layout

下面这些布局名称和字段是后续扩展的预期约定，供前端联测和文档对齐使用，当前可以先按这些名字准备内容：

| layout | 预期字段 |
|---|---|
| `section_divider` | `title`, `subtitle`, `section`, `accent`, `notes` |
| `quote` | `quote`, `author`, `context`, `notes` |
| `comparison` | `left_title`, `right_title`, `left_items`, `right_items`, `summary`, `notes` |
| `process` | `title`, `steps`, `inputs`, `outputs`, `notes` |
| `matrix` | `title`, `quadrants`, `axis_x`, `axis_y`, `highlights`, `notes` |
| `architecture` | `title`, `modules`, `layers`, `links`, `notes` |

说明：

- `section_divider`：适合章节页、转场页、阶段切换页。
- `quote`：适合金句页、结论页、态度表达页。
- `comparison`：适合对比页、方案取舍页、前后版本页。
- `process`：适合流程页、步骤页、操作链路页。
- `matrix`：适合四象限页、优先级页、分类判断页。
- `architecture`：适合架构模块页、系统结构页、能力分层页。

### GET `/ppt/themes`

返回当前支持的主题。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    { "theme_id": "tech", "label": "科技风" },
    { "theme_id": "business", "label": "商务风" },
    { "theme_id": "minimal", "label": "简约风" }
  ]
}
```

### POST `/ppt/decks`

根据文本或聊天记录生成 PPT deck。`theme` 支持中文值如 `科技风`，服务端会归一化为 `tech`。如果 `content` 中出现明确页数（如 `生成 3 页`、`做 6 页`、`输出 8-10 页`），服务端会优先使用消息里的页数；范围写法取上限，并统一限制在 `1-20`，覆盖 `preferences.slides_limit`。

**请求体**

```json
{
  "type": "chat_record",
  "content": "今天团队讨论了项目进度，需要生成 PPT 总结。",
  "preferences": {
    "theme": "科技风",
    "slides_limit": 10,
    "author": "user123"
  }
}
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "deck_id": "deck_xxx",
    "type": "chat_record",
    "title": "string",
    "source_content": "string",
    "theme": "tech",
    "author": "user123",
    "version": 1,
    "last_modified": "2026-04-28T12:00:00Z",
    "slides": [
      {
        "id": "slide_xxx",
        "slide_id": "slide_xxx",
        "title": "第一页标题",
        "body": ["要点 1"],
        "images": [],
        "notes": "讲稿备注",
        "theme": "tech",
        "author": "user123",
        "last_modified": "2026-04-28T12:00:00Z",
        "version": 1
      }
    ],
    "html": "<!DOCTYPE html>...",
    "history": []
  }
}
```

### POST `/ppt/decks/{deck_id}/modify`

通过自然语言修改 deck。可传 `slide_id` 做增量修改；目标 slide 的 `version` 会递增，deck 的 `version` 与 `last_modified` 也会更新。

**请求体**

```json
{
  "instruction": "把第二页的标题改为“下周计划”",
  "slide_id": "slide_xxx"
}
```

**响应**

返回更新后的 deck，结构同 `POST /ppt/decks`。

### POST `/ppt/decks/{deck_id}/export`

把当前 deck 同步导出为 PPTX。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "deck_id": "deck_xxx",
    "file_name": "deck.pptx",
    "path": "/absolute/path/to/deck.pptx",
    "url": null,
    "version": 2
  }
}
```

### 运行时说明

当前实现会把 HTML 和 JSON 产物保存到 `GENERATED_ROOT/ppt/{deck_id}/`。PPTX 导出优先使用 Node.js 和 `pptxgenjs` 生成原生幻灯片；如果本机运行时不可用，服务会返回一个可追踪的 fallback 文件，保证 demo 链路和 API 契约不中断。

PPT 生成与自然语言修改必须配置 DeepSeek 兼容接口，当前默认模型为 `deepseek-v4-flash`。未配置 `AGENT_API_KEY` 时，生成和修改接口会返回 `503`，不会走本地内容 fallback。

---

## 9. 工作台

Workspace 是用于承载协作状态的后端容器。当前只暴露轻量元数据。

### GET `/workspace/{workspace_id}`

返回工作台元信息。

**路径参数**

- `workspace_id`：工作台标识

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "workspace_id": "string",
    "role": "string",
    "locked": false
  }
}
```

---

## 10. 同步

Sync 分组用于预留实时传输能力的发现入口，当前只描述传输元数据，不代表已经定义完整消息协议。

### GET `/sync/ws/{session_id}`

返回某个会话的同步通道信息。

**路径参数**

- `session_id`：同步会话标识

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "string",
    "transport": "websocket"
  }
}
```

---

## 10. 系统

### GET `/system/ping`

健康检查接口。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok",
    "timestamp": "2026-04-26T10:00:00Z"
  }
}
```

---

## 11. 说明

- 基础路径保持 `/api/v1`
- 路由命名已与当前后端骨架和 OpenAPI 摘要对齐
- 旧的 `sessions`、`settings`、`webhook`、旧 Agent 执行/历史接口，以及旧 Canvas 快照/元素/版本文档已移除，等待对应框架路由真正恢复后再补
