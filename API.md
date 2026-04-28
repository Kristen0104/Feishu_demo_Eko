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

PPT 模块独立于 `canvas/board`。它负责生成和预览单文件 HTML deck，不参与飞书白板节点渲染，也不会复用 `board` 的导图/便签流程。

### POST `/ppt/tasks`

创建一个 HTML PPT 生成任务。

**请求体**

```json
{
  "topic": "string",
  "prompt": "string",
  "title": "string"
}
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "string",
    "topic": "string",
    "prompt": "string",
    "title": "string",
    "status": "pending",
    "current_step": "pending",
    "artifact_kind": "html",
    "preview_url": "/api/v1/ppt/tasks/{task_id}/preview",
    "artifact_path": null,
    "pptx_path": null,
    "pptx_download_url": null,
    "error_message": null,
    "logs": []
  }
}
```

### GET `/ppt/tasks/{task_id}`

查询 HTML PPT 任务状态。

### POST `/ppt/tasks/{task_id}/run`

执行 HTML PPT 生成任务。当前实现会生成单文件 `index.html`，并把产物保存到 `backend/generated/ppt_html/{task_id}/index.html`。

### POST `/ppt/tasks/{task_id}/export-pptx`

基于已生成的 HTML deck 导出 `.pptx` 文件。当前实现会先把每一页渲染为 PNG，再将这些 PNG 组装为 PowerPoint 文件，因此导出的页面视觉保真度较高，但单页内容默认不是 PowerPoint 原生可编辑元素。

导出成功后，任务对象会补充：

- `pptx_path`
- `pptx_download_url`

### GET `/ppt/tasks/{task_id}/download-pptx`

下载导出的 PPTX 文件。

**响应**

- `200 OK`
- `Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation`

### GET `/ppt/tasks/{task_id}/preview`

返回任务对应的 HTML 产物预览。

**响应**

- `200 OK`
- `Content-Type: text/html`

### 导出运行时说明

`export-pptx` 依赖服务端可用的 Node.js、Playwright 和 Chromium 浏览器内核：

- `PPT_EXPORT_NODE_BIN`
- `PPT_EXPORT_NODE_MODULES`
- Playwright Chromium 浏览器

生产环境建议在导出 worker 或后端容器镜像中预装这些依赖。

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
