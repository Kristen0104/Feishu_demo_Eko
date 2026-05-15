# Eko API 接口说明

**版本**：v1  
**日期**：2026-05-15  
**基础路径**：`/api/v1`

---

## 1. 通用说明

### 1.1 统一约定

| 项 | 说明 |
|----|------|
| 基础路径 | `/api/v1` |
| 鉴权 | `Authorization: Bearer {token}` |
| 响应格式 | `ApiResponse<T>` JSON |
| 实时协议 | WebSocket / SSE，结合 Redis Pub/Sub |

### 1.2 通用响应

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

---

## 2. 认证与用户

### 2.1 邮箱密码注册

`POST /auth/register`

### 2.2 邮箱密码登录

`POST /auth/login`

### 2.3 飞书登录授权地址

`GET /auth/feishu/login-url`

### 2.4 飞书登录

`POST /auth/feishu/login`

### 2.5 飞书 OAuth 回调登录

`GET /auth/feishu/callback`

### 2.6 当前用户

`GET /auth/me`

### 2.7 修改当前用户资料

`PATCH /auth/me`

### 2.8 上传头像

`POST /auth/me/avatar`

### 2.9 修改密码

`PATCH /auth/me/password`

### 2.10 绑定飞书账号

`POST /auth/feishu/bind`

---

## 3. Agent

### 3.1 创建任务骨架

`POST /agent/tasks`

### 3.2 Agent 对话

`POST /agent/chat`

### 3.3 Agent 流式对话

`POST /agent/chat/stream`

说明：
- 自动识别 `chat`、`docx`、`ppt`、`board` 意图。
- 若传入 `forced_intent`，服务端会优先按该意图执行。
- 运行时会进入 `context -> retrieval -> planner -> tool_execute` 流程。

---

## 4. RAG

### 4.1 文件列表

`GET /rag/files`

### 4.2 删除文件

`DELETE /rag/files/{file_id}`

### 4.3 文件入库

`POST /rag/files`

### 4.4 上传文件并入库

`POST /rag/files/upload`

### 4.5 RAG 检索

`GET /rag/search?query=...&limit=8`

说明：
- 默认 `limit=8`
- 最大 `limit=20`
- 当前实现使用 Embedding + pgvector cosine distance 排序，没有独立 reranker

---

## 5. 飞书与画板

### 5.1 飞书卡片骨架

`GET /feishu/cards/{card_id}`

### 5.2 飞书画板导入

`POST /feishu/board/import`

### 5.3 创建飞书画板节点

`POST /feishu/board/create-notes`

### 5.4 获取飞书画板节点

`GET /feishu/board/nodes/{whiteboard_id}`

### 5.5 获取飞书画板图片

`GET /feishu/board/image/{whiteboard_id}`

### 5.6 更新飞书画板

`POST /feishu/board/update`

### 5.7 删除飞书画板节点

`POST /feishu/board/delete`

### 5.8 发布 Markdown 到飞书

`POST /feishu/sync/publish`

### 5.9 查询导入任务状态

`GET /feishu/sync/status/{ticket}`

### 5.10 飞书事件回调

`POST /feishu/events`

---

## 6. Bitable

### 6.1 发现状态

`GET /bitable/discovery/status`

### 6.2 列出可选多维表格

`GET /bitable/discovery/bases`

### 6.3 解析多维表格链接

`POST /bitable/discovery/resolve-url`

### 6.4 列出表

`GET /bitable/discovery/tables`

### 6.5 列出视图

`GET /bitable/discovery/views`

### 6.6 列出字段

`GET /bitable/discovery/fields`

### 6.7 列出数据源

`GET /bitable/sources`

### 6.8 新增数据源

`POST /bitable/sources`

### 6.9 更新数据源

`PATCH /bitable/sources/{source_id}`

### 6.10 删除数据源

`DELETE /bitable/sources/{source_id}`

### 6.11 检查数据源结构

`POST /bitable/sources/{source_id}/inspect`

### 6.12 获取 schema 摘要

`GET /bitable/schema`

### 6.13 查询记录

`POST /bitable/query`

### 6.14 归档产物

`POST /bitable/archive`

---

## 7. 同步

### 7.1 同步通道骨架

`GET /sync/ws/{session_id}`

### 7.2 会话列表

`GET /sync/sessions`

### 7.3 会话详情

`GET /sync/sessions/{session_id}`

### 7.4 删除会话

`DELETE /sync/sessions/{session_id}`

### 7.5 选择上下文并运行 Agent

`POST /sync/sessions/{session_id}/context/selection`

### 7.6 WebSocket 连接

`WS /sync/ws/session/{session_id}`

---

## 8. 团队协作

### 8.1 团队成员列表

`GET /team/members`

### 8.2 邀请成员

`POST /team/members/invite`

### 8.3 移除成员

`DELETE /team/members/{member_id}`

### 8.4 邀请成员加入会话协作

`POST /team/sessions/{session_id}/invites`

### 8.5 获取会话邀请

`GET /team/sessions/{session_id}/invites`

### 8.6 获取我的会话邀请

`GET /team/session-invites`

### 8.7 处理邀请

`PATCH /team/session-invites/{invite_id}`

---

## 9. 补充说明

- Agent 意图识别由 `RouterAgent.classify_chat_intent()` 负责。
- RAG 检索默认走 Embedding + pgvector 相似度排序。
- Bitable 查询和归档都是可选能力，失败不会阻断主任务。
- Redis 用于实时广播和状态同步，不只是缓存。
