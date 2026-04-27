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
- `workspace`
- `sync`
- `system`

这些分组定义了当前重构后的框架级路由面，后续可以继续扩展业务，但不会改变这套基础分组。

---

## 3. 鉴权

### 鉴权说明

- 当前登录方式基于飞书认证。
- 受保护接口使用 Bearer Token 鉴权。
- 文档只保留当前 stub 已暴露的身份字段。

### POST `/auth/feishu/login`

使用飞书登录 `code` 换取访问令牌和基础用户信息。

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

返回当前登录用户的 stub 信息。

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

---

## 4. Canvas

Canvas 是当前内容工作台的画板协作模块。现阶段已经支持单会话的飞书文档导入、working board 读取与编辑、AI patch 生成与应用、冲突审查、导出与发布回飞书。

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

### GET `/canvas/sessions/{session_id}/detail`

返回当前画板会话的完整调试态数据，包含：

- `session`
- `source_board`
- `working_board`
- `element_mappings`
- `recent_changes`
- `merge_reviews`

前端联调页以这个接口作为主状态源。

### POST `/canvas/sessions/{session_id}/import-feishu-document`

输入飞书文档 `share_url`，解析文档中的首个 whiteboard，并把结果导入到当前 canvas session。返回 `CanvasSessionDetail`。

### POST `/canvas/sessions/{session_id}/import-mermaid`

把 Mermaid 语法导入到当前 canvas session 关联的飞书白板，并在导入后刷新 working board。

**请求体**

```json
{
  "code": "graph TD; A-->B;",
  "syntax_type": 2,
  "style_type": 1,
  "diagram_type": 0
}
```

### POST `/canvas/sessions/{session_id}/refresh-feishu-document`

重新读取同一飞书文档的首个 whiteboard 并刷新 source board。

- 如果 source version 未变化：保持 `sync_state=idle`
- 如果 source version 已变化且本地 working board 已编辑：保留 working board，不覆盖用户内容，并切到 `sync_state=conflict`

### POST `/canvas/sessions/{session_id}/refresh-feishu-document-review`

执行刷新并在检测到 source conflict 时自动创建或复用 merge review。

### POST `/canvas/sessions/{session_id}/changes`

提交单次 working board 变更。当前主要用于前端把 Tldraw 画布内容回写到：

- `working_board.latest_snapshot`
- `working_board.crdt_document`
- `element_mappings`
- `recent_changes`

### POST `/canvas/sessions/{session_id}/generate`

生成画板 patch。

- `full_board`：生成整板草稿
- `targeted_patch`：针对选区生成节点替换或新增操作

### POST `/canvas/sessions/{session_id}/apply-patch`

把生成结果应用到当前 working board，并记录 `ai_patch` 变更。

### GET `/canvas/sessions/{session_id}/merge-reviews`

列出当前会话的 merge review。

### POST `/canvas/sessions/{session_id}/merge-resolve`

提交冲突解决结果。当前支持针对每个 conflict 选择：

- `source`
- `working`

### POST `/canvas/sessions/{session_id}/export-feishu-board`

导出当前 canvas session 为飞书画板适配格式。默认情况下，若仍存在未解决冲突则返回 `409`。

### POST `/canvas/sessions/{session_id}/publish-feishu-board`

在 export 成功的基础上，把结果发布回飞书。

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

飞书面当前除了卡片元数据读取，还保留了画板语法导入、白板节点读取和发布适配的接口，便于 Canvas 工作台直接对接飞书白板。

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

### POST `/feishu/boards/{whiteboard_id}/syntax-import`

把语法图导入到指定飞书白板。当前代码路径会把请求转给飞书白板的语法导入接口，适合 PlantUML / Mermaid 这类文本图表。

**路径参数**

- `whiteboard_id`：飞书白板标识

**请求体**

```json
{
  "code": "graph TD; A-->B;",
  "syntax_type": 2,
  "style_type": 1,
  "diagram_type": 0
}
```

### POST `/feishu/boards/{whiteboard_id}/mermaid-import`

Mermaid 语法导入的便捷入口。默认把 `syntax_type` 固定为 `2`，其余字段与通用语法导入一致，前端可以直接把 Mermaid 文本提交到当前白板。

**请求体**

```json
{
  "code": "graph TD; A-->B;",
  "style_type": 1,
  "diagram_type": 0
}
```

---

## 8. 工作台

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

## 9. 同步

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
