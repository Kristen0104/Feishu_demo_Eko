# Eko API 接口文档

**版本**：v2.0
**日期**：2026-05-05
**基础路径**：`/api/v1`

---

## 1. 总览

本文档描述后端 `/api/v1` 下的所有接口，按模块分组。

### 1.1 通用约定

| 项目 | 说明 |
|------|------|
| 基础路径 | `/api/v1` |
| 鉴权头 | `Authorization: Bearer {token}` |
| 数据格式 | JSON |
| 通用包裹 | `ApiResponse` |

### 1.2 通用响应包裹

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 1.3 路由模块

- `auth` - 认证
- `agent` - Agent 任务
- `aippt` - AI PPT 生成
- `canvas` - 画板会话
- `document` - 文档生成
- `feishu` - 飞书集成
- `rag` - 知识库检索
- `sync` - 实时同步
- `team` - 团队管理
- `system` - 系统

---

## 2. 认证 (Auth)

### POST `/auth/register`

邮箱密码注册。

**请求体**
```json
{
  "email": "string",
  "password": "string",
  "display_name": "string"
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
      "email": "string"
    }
  }
}
```

---

### POST `/auth/login`

邮箱密码登录。

**请求体**
```json
{
  "email": "string",
  "password": "string"
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
      "email": "string"
    }
  }
}
```

---

### GET `/auth/me`

返回当前登录用户信息。

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
    "email": "string"
  }
}
```

---

### GET `/auth/feishu/login-url`

生成飞书 OAuth 授权 URL。

**查询参数**
- `redirect_uri`：可选

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

---

### POST `/auth/feishu/login`

使用飞书 code + state 登录。

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

---

### GET `/auth/feishu/callback`

飞书 OAuth 回调入口。

**查询参数**
- `code`：飞书回调 code
- `state`：一次性 state
- `redirect_uri`：可选

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

---

## 3. Agent

### POST `/agent/tasks`

创建 Agent 任务。

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

### POST `/agent/chat`

Agent 对话（非流式）。

**请求体**
```json
{
  "session_id": "string",
  "message": "string",
  "context": {
    "chat_history": [
      { "role": "user", "content": "string" },
      { "role": "assistant", "content": "string" }
    ]
  }
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "response": "string",
    "session_id": "string"
  }
}
```

---

### POST `/agent/chat/stream`

Agent 对话（流式），返回 SSE。

**请求体**
```json
{
  "session_id": "string",
  "message": "string",
  "context": {
    "chat_history": []
  }
}
```

**响应** (text/event-stream)
```
data: {"event": "...", "data": {...}}

data: {"event": "...", "data": {...}}
```

---

## 4. AI PPT (AIPPT)

### GET `/aippt/design-modes`

获取 PPT 生成模式选项。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "mode": "template",
      "label": "模板",
      "description": "使用稳定模板布局生成 PPT，速度更快、结果更可控。"
    },
    {
      "mode": "free_design",
      "label": "自由设计",
      "description": "逐页自由设计并可使用生图能力，适合更强视觉表现。"
    }
  ]
}
```

---

### POST `/aippt/generate`

创建 PPT 生成任务。

**请求体** (JSON)
```json
{
  "topic": "string",
  "page_count": 6,
  "style": "clean_business",
  "design_mode": "template",
  "source_url": "string"
}
```

或 **multipart/form-data**：
- `topic`：PPT 主题
- `page_count`：页数（默认 6）
- `style`：风格
- `design_mode`：设计模式
- `source_url`：来源 URL
- `file`：上传文件
- `image_files`：图片文件列表

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "string",
    "status": "pending",
    "created_at": "2026-05-05T00:00:00Z"
  }
}
```

---

### GET `/aippt/jobs/{job_id}`

查询 PPT 任务状态。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "string",
    "status": "completed|pending|failed",
    "created_at": "2026-05-05T00:00:00Z"
  }
}
```

---

### GET `/aippt/preview/{job_id}`

获取 PPT 预览结构。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "string",
    "slides": [
      {
        "slide_number": 1,
        "title": "string",
        "svg": "string"
      }
    ]
  }
}
```

---

### GET `/aippt/preview/{job_id}/slides/{slide_number}`

获取单页 SVG 预览。

**响应**
- Content-Type: `image/svg+xml`
- 内容：SVG 文件

---

### GET `/aippt/files/{job_id}`

下载生成的 PPTX 文件。

**响应**
- Content-Type: `application/vnd.openxmlformats-officedocument.presentationml.presentation`
- Content-Disposition: `attachment; filename="{job_id}.pptx"`

---

## 5. Canvas

### GET `/canvas/sessions/{session_id}`

获取 Canvas 会话信息。

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

### POST `/canvas/board/tasks`

创建飞书画板任务。

**请求体**
```json
{
  "session_id": "string",
  "instruction": "string",
  "whiteboard_id": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "string",
    "status": "pending"
  }
}
```

---

### GET `/canvas/board/tasks/{task_id}`

获取飞书画板任务状态。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "string",
    "status": "pending|running|completed|failed"
  }
}
```

---

### POST `/canvas/board/tasks/{task_id}/run`

执行飞书画板任务。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "string",
    "status": "running"
  }
}
```

---

## 6. 文档 (Document)

### POST `/document/generate`

生成文档（非流式）。

**请求体**
```json
{
  "session_id": "string",
  "topic": "string",
  "document_type": "meeting_notes|project_plan|report|proposal",
  "requirement": "string",
  "tone": "formal|casual|technical"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "string",
    "status": "completed",
    "content": "# 文档内容..."
  }
}
```

---

### POST `/document/generate/stream`

生成文档（流式）。

**请求体**：同 `/document/generate`

**响应** (text/event-stream)
```
data: {"session_id": "xxx", "status": "generating"}

data: {"content": "## 第一部分..."}

data: {"status": "completed"}
```

---

### POST `/document/save`

保存文档并可选同步到飞书。

**请求体**
```json
{
  "session_id": "string",
  "title": "string",
  "content": "string",
  "sync_to_feishu": false,
  "app_token": "string",
  "table_id": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "string",
    "status": "saved|saving",
    "message": "文档已保存"
  }
}
```

---

### POST `/document/sync`

自动同步 Markdown 文档到飞书。

**请求体**
```json
{
  "session_id": "string",
  "content": "string",
  "current_url": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "string",
    "status": "completed",
    "message": "文档同步完成",
    "document_url": "string"
  }
}
```

---

## 7. 飞书 (Feishu)

### GET `/feishu/cards/{card_id}`

获取飞书卡片信息。

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

### POST `/feishu/board/import`

导入图表到飞书画板。

**请求体**
```json
{
  "diagram_content": "string",
  "title": "string",
  "whiteboard_id": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "whiteboard_id": "string",
    "status": "imported"
  }
}
```

---

### POST `/feishu/board/create-notes`

创建飞书画板节点。

**请求体**
```json
{
  "whiteboard_id": "string",
  "parent_node_id": "string",
  "content": "string",
  "position": { "x": 0, "y": 0 }
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "node_id": "string",
    "status": "created"
  }
}
```

---

### GET `/feishu/board/nodes/{whiteboard_id}`

获取飞书画板节点。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "whiteboard_id": "string",
    "nodes": []
  }
}
```

---

### GET `/feishu/board/image/{whiteboard_id}`

获取飞书画板图片。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "image_url": "string"
  }
}
```

---

### POST `/feishu/board/update`

更新飞书画板内容。

**请求体**
```json
{
  "whiteboard_id": "string",
  "node_id": "string",
  "content": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "updated"
  }
}
```

---

### POST `/feishu/board/delete`

删除飞书画板节点。

**请求体**
```json
{
  "whiteboard_id": "string",
  "node_id": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "deleted"
  }
}
```

---

### POST `/feishu/sync/publish`

发布 Markdown 文档到飞书（异步）。

**请求体**
```json
{
  "markdown_content": "string",
  "title": "string",
  "session_id": "string",
  "app_token": "string",
  "table_id": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "ticket": "string",
    "status": "processing"
  }
}
```

---

### GET `/feishu/sync/status/{ticket}`

查询导入任务状态。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "ticket": "string",
    "status": "pending|processing|completed|failed",
    "result_url": "string"
  }
}
```

---

### POST `/feishu/events`

飞书事件回调。

---

## 8. 知识库 (RAG)

### GET `/rag/files`

获取 RAG 文件列表。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "file_id": "string",
      "filename": "string",
      "source": "string",
      "created_at": "2026-05-05T00:00:00Z"
    }
  ]
}
```

---

### POST `/rag/files`

RAG 文件入库。

**请求体**
```json
{
  "filename": "string",
  "source": "string",
  "content": "string",
  "metadata": {}
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "file_id": "string",
    "filename": "string",
    "status": "ingested"
  }
}
```

---

### POST `/rag/files/upload`

上传并解析 RAG 文件。

**请求体** (multipart/form-data)
- `file`：文件
- `source`：来源（可选）
- `metadata`：JSON 元数据（可选）

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "file_id": "string",
    "filename": "string",
    "status": "ingested"
  }
}
```

---

### DELETE `/rag/files/{file_id}`

删除 RAG 文件及其向量块。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

---

### GET `/rag/search`

RAG 知识库检索。

**查询参数**
- `query`：检索词（必填）
- `limit`：返回数量，默认 8，最大 20

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "query": "string",
    "results": [
      {
        "file_id": "string",
        "filename": "string",
        "chunk_text": "string",
        "score": 0.95
      }
    ]
  }
}
```

---

## 9. 同步 (Sync)

### GET `/sync/ws/{session_id}`

获取同步通道信息。

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

### GET `/sync/sessions`

获取会话列表。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": []
}
```

---

### GET `/sync/sessions/{session_id}`

获取会话详情。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "string",
    "status": "string"
  }
}
```

---

### DELETE `/sync/sessions/{session_id}`

删除会话。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "string",
    "deleted": true
  }
}
```

---

### POST `/sync/sessions/{session_id}/context/selection`

选择上下文并运行 Agent。

**请求体**
```json
{
  "start_index": 0,
  "end_index": 5,
  "instruction": "string"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "response": "string"
  }
}
```

---

### WebSocket `/sync/ws/session/{session_id}`

实时会话 WebSocket 连接。

---

## 10. 团队 (Team)

### GET `/team/members`

获取团队成员列表。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "member_id": "string",
      "display_name": "string",
      "email": "string",
      "role": "owner|member",
      "joined_at": "2026-05-05T00:00:00Z"
    }
  ]
}
```

---

### POST `/team/members/invite`

按邮箱邀请团队成员。

**请求体**
```json
{
  "email": "string",
  "role": "member"
}
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "member_id": "string",
    "email": "string",
    "status": "invited"
  }
}
```

---

### DELETE `/team/members/{member_id}`

移除团队成员。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

---

## 11. 系统 (System)

### GET `/system/ping`

健康检查。

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok",
    "timestamp": "2026-05-05T00:00:00Z"
  }
}
```

---

## 12. 错误码

| code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 业务验证失败 |
| 502 | LLM 服务错误 |
| 500 | 服务器内部错误 |