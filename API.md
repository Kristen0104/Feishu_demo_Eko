# Eko API 接口定义规范

**版本**：v1.1
**日期**：2026-04-24  
**基础路径**：`/api/v1`

---

## 1. 协议说明

### 1.1 通用约定

| 项 | 说明 |
|----|------|
| **基础路径** | `/api/v1` |
| **鉴权** | Header: `Authorization: Bearer {token}` |
| **实时协议** | WebSocket 配合 Redis Pub/Sub 实现 |
| **响应格式** | JSON |

### 1.2 通用响应结构

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

---

## 2. 用户与会话管理 (Auth & Sessions)

### 2.1 身份验证

#### POST /auth/feishu/login

接收飞书 code 获取令牌。

**请求体:**
```json
{
  "code": "string",
  "state": "string"
}
```

**响应:**
```json
{
  "code": 0,
  "data": {
    "access_token": "string",
    "expires_in": 7200,
    "user": {
      "id": "string",
      "name": "string",
      "avatar": "string"
    }
  }
}
```

#### GET /auth/me

获取当前用户信息、权限及飞书关联状态。

**响应:**
```json
{
  "code": 0,
  "data": {
    "id": "string",
    "name": "string",
    "avatar": "string",
    "feishu_connected": true,
    "permissions": ["create", "edit", "delete"]
  }
}
```

### 2.2 会话生命周期

#### GET /sessions

分页获取会话列表（含最后一次意图、更新时间）。

**Query 参数:**
- `page`: 页码 (默认 1)
- `limit`: 每页数量 (默认 20)

**响应:**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "string",
        "title": "string",
        "last_intent": "CHAT|DOC|PPT|SUMMARY",
        "updated_at": "2026-04-24T10:00:00Z",
        "is_pinned": false
      }
    ],
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

#### POST /sessions

手动新建空会话。

**请求体:**
```json
{
  "title": "string (可选)"
}
```

**响应:**
```json
{
  "code": 0,
  "data": {
    "id": "string",
    "title": "string",
    "created_at": "2026-04-24T10:00:00Z"
  }
}
```

#### PATCH /sessions/{id}

更新标题、置顶状态或清除上下文。

**请求体:**
```json
{
  "title": "string (可选)",
  "is_pinned": true (可选),
  "clear_context": false (可选)
}
```

#### DELETE /sessions/{id}

删除会话及其关联的所有临时缓存。

#### POST /sessions/{session_id}/context

清除会话上下文（历史对话记录）。

**响应:**
```json
{
  "code": 0,
  "data": {
    "status": "cleared"
  }
}
```

### 2.3 任务列表

#### GET /sessions/{session_id}/tasks

获取会话下的所有任务列表。

**响应:**
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "string",
        "message": "string",
        "result": "string",
        "intent": "CHAT|DOC|PPT|SUMMARY",
        "status": "running|completed|failed|cancelled",
        "created_at": "2026-04-24T10:00:00Z"
      }
    ]
  }
}
```

---

## 3. 知识库管理 (Knowledge & RAG)

### 3.1 文件管理

#### GET /rag/files

获取当前会话/全局知识库文件列表及处理状态。

**Query 参数:**
- `session_id`: 会话 ID (可选，不传则返回全局)
- `status`: 过滤状态 `pending|processing|completed|failed` (可选)

**响应:**
```json
{
  "code": 0,
  "data": [
    {
      "id": "string",
      "filename": "string",
      "status": "completed",
      "chunk_count": 10,
      "created_at": "2026-04-24T10:00:00Z"
    }
  ]
}
```

#### POST /rag/ingest

上传文件（Multipart）或输入 URL，触发分片与向量化。

**请求 (Multipart Form):**
- `file`: 文件 (可选)
- `url`: URL (可选)
- `session_id`: 会话 ID (可选)

**响应:**
```json
{
  "code": 0,
  "data": {
    "file_id": "string",
    "status": "processing"
  }
}
```

#### DELETE /rag/files/{file_id}

从向量库和存储中彻底移除。

### 3.2 向量检索调试

#### POST /rag/search/test

仅返回检索到的 Top-K 文本片段（不调用 LLM），用于调试 RAG 准确度。

**请求体:**
```json
{
  "query": "string",
  "k": 5,
  "session_id": "string (可选)"
}
```

**响应:**
```json
{
  "code": 0,
  "data": [
    {
      "content": "string",
      "score": 0.95,
      "source_file": "string"
    }
  ]
}
```

---

## 4. Agent 核心控制 (Agent Brain)

### 4.1 任务执行

#### POST /agent/execute

投递指令（主入口）。支持 `stream=true` 模式。

**请求体:**
```json
{
  "session_id": "string",
  "query": "帮我梳理运营方案",
  "stream": true,
  "intent_hint": "DOC|PPT|CHAT (可选)"
}
```

**响应 (非 stream 模式):**
```json
{
  "code": 0,
  "data": {
    "task_id": "string",
    "intent": "DOC",
    "result": {}
  }
}
```

**Stream 事件流:**
```
data: {"type":"INTENT_RECOGNIZED","payload":{"intent":"DOC"}}
data: {"type":"AGENT_PLANNING","payload":{"steps":[...]}}
data: {"type":"DOC_STREAM","payload":{"chunk":"# 运营方案..."}}
data: {"type":"TASK_COMPLETED","payload":{"result_url":"..."}}
```

#### POST /agent/stop

强制中断当前正在运行的 Agent 任务（任务终止/紧急停止）。

**请求体:**
```json
{
  "task_id": "string"
}
```

### 4.2 任务回溯

#### GET /agent/status

获取 Agent 当前运行状态，用于前端轮询。

**响应:**
```json
{
  "code": 0,
  "data": {
    "status": "idle|running",
    "current_task_id": "string (running时才有)"
  }
}
```

#### GET /agent/tasks/{task_id}/plan

获取当前任务被拆解后的 JSON 步骤。

**响应:**
```json
{
  "code": 0,
  "data": {
    "task_id": "string",
    "steps": [
      {
        "id": "1",
        "name": "意图分析",
        "status": "completed",
        "result": {}
      }
    ]
  }
}
```

#### GET /agent/history

获取该会话下的所有指令与执行结果历史（用于上下文注入）。

**Query 参数:**
- `session_id`: 会话 ID

**响应:**
```json
{
  "code": 0,
  "data": [
    {
      "role": "user",
      "content": "string",
      "timestamp": "2026-04-24T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "string",
      "timestamp": "2026-04-24T10:00:05Z"
    }
  ]
}
```

---

## 5. 画布与文档同步 (Canvas & Doc)

> ⚠️ **TODO**: Canvas 模块后续可能采用开源方案（如 Tldraw、Excalidraw）实现，
> 当前接口设计存在不确定性，实际接口可能在此基础上调整。

### 5.1 状态快照

#### GET /canvas/{session_id}

拉取当前画布全量 Tldraw JSON 数据。

**响应:**
```json
{
  "code": 0,
  "data": {
    "tldraw": { /* Tldraw JSON 格式 */ },
    "version": 10,
    "updated_at": "2026-04-24T10:00:00Z"
  }
}
```

#### POST /canvas/snapshot

存入当前画布状态快照（防止 AI 生成过程中数据丢失）。

**请求体:**
```json
{
  "session_id": "string",
  "tldraw": { /* Tldraw JSON 格式 */ },
  "version": 11
}
```

### 5.2 协作交互

#### PATCH /canvas/elements

增量更新元素（移动、改色、修改文字）。

**请求体:**
```json
{
  "session_id": "string",
  "upsert": [
    {
      "id": "string",
      "type": "text",
      "props": { "text": "新内容", "x": 100, "y": 100 }
    }
  ],
  "delete": ["element_id_1"]
}
```

#### GET /canvas/versions

获取历史版本记录，支持回滚。

**Query 参数:**
- `session_id`: 会话 ID

**响应:**
```json
{
  "code": 0,
  "data": [
    {
      "version": 10,
      "created_at": "2026-04-24T10:00:00Z",
      "snapshot_url": "string"
    }
  ]
}
```

---

## 6. 飞书集成与设置 (Integration)

### 6.1 Bitable 同步配置

#### GET /settings/feishu/bitable/tables

获取飞书多维表格的所有数据表。

**响应:**
```json
{
  "code": 0,
  "data": [
    {
      "app_token": "string",
      "table_id": "string",
      "name": "string"
    }
  ]
}
```

#### GET /settings/feishu/bitable/fields

获取特定数据表的字段列表（用于配置映射）。

**Query 参数:**
- `app_token`: App Token
- `table_id`: Table ID

**响应:**
```json
{
  "code": 0,
  "data": [
    {
      "field_id": "string",
      "field_name": "string",
      "type": "text|number|date"
    }
  ]
}
```

#### POST /settings/feishu/bitable/config

设置同步目标（AppToken, TableID）。

**请求体:**
```json
{
  "app_token": "string",
  "table_id": "string",
  "field_mapping": {
    "title": "field_id_1",
    "content_url": "field_id_2",
    "created_at": "field_id_3"
  }
}
```

#### GET /settings/feishu/bitable/config

获取当前已保存的 Bitable 同步配置。

**响应:**
```json
{
  "code": 0,
  "data": {
    "app_token": "string",
    "table_id": "string",
    "field_mapping": {
      "title": "field_id_1",
      "content_url": "field_id_2",
      "created_at": "field_id_3"
    }
  }
}
```

### 6.2 飞书 Webhook (后端专用)

#### POST /webhook/feishu

接收飞书开放平台的消息事件（IM 消息、语音、卡片点击）。

**响应:**
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "chat_id": "string",
    "message_id": "string",
    "text": "string",
    "clean_text": "string",
    "sender": "string",
    "intent": "CHAT|DOC|PPT|SUMMARY",
    "chat_type": "group|private",
    "chat_history": [
      {
        "message_id": "string",
        "sender_id": "string",
        "content": "string",
        "create_time": "string"
      }
    ]
  }
}
```

### 6.3 飞书长连接 (WebSocket)

飞书长连接 WebSocket 服务用于接收飞书事件，实现方式参见 [feishu_ws.py](backend/app/feishu_ws.py)。

---

## 7. 实时同步消息 (WebSocket Payloads)

| type (事件) | payload (数据内容) | 业务场景 |
|-------------|-------------------|----------|
| `INTENT_RECOGNIZED` | `{ intent: 'CHAT'\|'DOC'\|'PPT'\|'SUMMARY' }` | Agent 刚识别完意图，通知前端切换 UI 模式。 |
| `AGENT_PLANNING` | `{ steps: [] }` | 展示 Agent 正在拆解的任务链路。 |
| `DOC_STREAM` | `{ chunk: '' }` | Word 文稿正在流式吐字。 |
| `CANVAS_UPDATE` | `{ upsert: [], delete: [] }` | 画布元素（卡片/连线）的实时增删。 |
| `TASK_COMPLETED` | `{ result_url: '', bitable_id: '' }` | 任务完成，告知最终成果路径。 |
| `CURSOR_SYNC` | `{ user_id: '', x: 0, y: 0 }` | 多端用户光标实时位置同步。 |

**WebSocket 连接路径:**
```
/ws/session/{session_id}?token={bearer_token}
```

---

## 8. 系统状态与错误

### 8.1 健康检查

#### GET /system/ping

健康检查。

**响应:**
```json
{
  "code": 0,
  "data": {
    "status": "ok",
    "timestamp": "2026-04-24T10:00:00Z"
  }
}
```

#### GET /system/check-db

检查数据库（PostgreSQL）连接状态。

**响应:**
```json
{
  "status": "ok",
  "postgres": "connected"
}
```

#### GET /system/check-redis

检查 Redis 连接状态。

**响应:**
```json
{
  "status": "ok",
  "redis": "connected"
}
```

### 8.2 错误码

| HTTP 状态码 | code | 说明 |
|-------------|------|------|
| 401 | 40100 | 认证失效 |
| 422 | 42200 | 意图无法识别（Agent 困惑） |
| 429 | 42900 | 达到 Token 消耗限制 |
| 502 | 50200 | 飞书 API 响应超时 |

**错误响应格式:**
```json
{
  "code": 40100,
  "message": "Authentication expired",
  "data": null
}
```

---

## 相关文档

- [PLAN.md](PLAN.md)
- [飞书长连接实现](backend/app/feishu_ws.py)
