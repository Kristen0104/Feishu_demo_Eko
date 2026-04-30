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
- `ppt`
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

## 6. PPT

`ppt` 模块用于把主题文本、URL 或上传文件转换成可编辑 PowerPoint。后端会先把输入统一转换成 Markdown / 纯文本，再调用 LLM 生成 `design_spec.md`、每页 SVG 和 `notes/total.md`，最后调用 `ppt-master` 导出 `.pptx`。

### POST `/ppt/generate`

创建一个 PPT 生成任务。

支持两种调用方式：

1. `application/json`
2. `multipart/form-data`

**JSON 请求体**

```json
{
  "topic": "AI 生成 PPT 系统设计",
  "page_count": 6,
  "style": "clean_business",
  "design_mode": "template",
  "source_url": null
}
```

**multipart/form-data 字段**

- `file`: 上传文件，可选
- `topic`: 主题文本，可选
- `source_url`: 页面 URL，可选
- `page_count`: 页数，可选，默认 `6`
- `style`: 风格，可选，默认 `clean_business`
- `design_mode`: 生成逻辑，可选，默认 `template`
  - `template`: 传统稳定模板渲染逻辑
  - `free_design`: PPT Master 对齐的自由 SVG Executor 逻辑

`free_design` 会按 `AIPPT_SLIDE_CONCURRENCY` 并发生成逐页 SVG，默认 `2`；PPT Master 后处理和导出仍保持 `total_md_split.py -> finalize_svg.py -> svg_to_pptx.py -s final`。

DeepSeek V4 Flash 默认关闭 thinking mode（`AIPPT_THINKING_ENABLED=false`），避免 SVG 执行型任务被推理模式拖慢；需要更强规划时可显式打开。

图片生成默认关闭。设置 `AIPPT_IMAGE_GENERATION_ENABLED=true` 和 `AIPPT_IMAGE_API_KEY` 后，后端会调用 `AIPPT_IMAGE_API_BASE/v1/images/generations` 的 `gpt-image-2`，把 `Pending` 图片写入 `project/images/` 并标记为 `Generated`；失败则标记 `Needs-Manual` 并继续 PPT Master 导出流程。

至少需要提供一种输入源：`topic`、`source_url` 或 `file`。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "string",
    "status": "queued",
    "progress": 0,
    "current_step": "任务已入队",
    "source_type": "topic",
    "source_name": "AI 生成 PPT 系统设计",
    "page_count": 6,
    "style": "clean_business",
    "design_mode": "template",
    "download_url": null,
    "error": null,
    "created_at": "2026-04-29T00:00:00+00:00",
    "updated_at": "2026-04-29T00:00:00+00:00"
  }
}
```

### GET `/ppt/jobs/{job_id}`

查询 PPT 任务状态。

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "string",
    "status": "generating_slides",
    "progress": 45,
    "current_step": "生成第 3 页 SVG",
    "source_type": "topic",
    "source_name": "AI 生成 PPT 系统设计",
    "page_count": 6,
    "style": "clean_business",
    "download_url": null,
    "error": null,
    "created_at": "2026-04-29T00:00:00+00:00",
    "updated_at": "2026-04-29T00:01:00+00:00"
  }
}
```

`status` 枚举：

- `queued`
- `parsing_file`
- `generating_design`
- `generating_slides`
- `generating_notes`
- `exporting`
- `done`
- `failed`

### GET `/ppt/files/{job_id}`

下载生成完成后的 `.pptx` 文件。

- 任务未完成时返回 `404`
- 成功时返回 PowerPoint 文件流，不使用 `ApiResponse` 包裹

---

## 7. RAG

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

## 8. 飞书

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
