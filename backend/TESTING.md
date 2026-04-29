# 后端测试指南

本指南说明如何在不配置飞书凭证的情况下测试后端功能。

---

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问 API 文档

打开浏览器访问：`http://localhost:8000/docs`

---

## 测试接口（无需飞书凭证）

### 测试 1: 生成模拟文档

**端点**: `POST /api/v1/document/test/generate`

**请求示例**:
```json
{
  "session_id": "test-session-001",
  "topic": "2024年度营销方案",
  "requirement": "请生成一份详细的年度营销方案，包含目标、策略、执行计划和预算",
  "document_type": "plan",
  "tone": "formal",
  "length": "medium"
}
```

**响应示例**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "test-session-001",
    "status": "completed",
    "content": "# 2024年度营销方案\n\n## 一、背景介绍\n...",
    "message": null
  }
}
```

---

### 测试 2: 保存文档（不调用飞书）

**端点**: `POST /api/v1/document/test/save`

**请求示例**:
```json
{
  "session_id": "test-session-001",
  "title": "2024年度营销方案",
  "content": "# 2024年度营销方案\n\n## 一、背景介绍\n...",
  "sync_to_feishu": false
}
```

---

## 完整流程测试（推荐）

1. **调用测试生成接口** → 获得 Markdown 内容
2. **前端展示并编辑** → 用户可修改内容
3. **调用测试保存接口** → 完成流程闭环

---

## 使用真实 LLM 测试（可选）

如果你想测试真实的 LLM 文档生成，需要配置 `.env`：

```env
# 火山引擎配置
VOLCENGINE_API_KEY=your_api_key_here
VOLCENGINE_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3
VOLCENGINE_MODEL=ep-your-endpoint-id
```

然后调用真实接口：`POST /api/v1/document/generate`

---

## 启用飞书同步（可选）

如需测试完整的飞书同步功能，配置 `.env`：

```env
# 飞书应用凭证
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=xxxxxx

# 飞书多维表格配置
FEISHU_BITABLE_APP_TOKEN=xxxxxx
FEISHU_BITABLE_TABLE_ID=xxxxxx
FEISHU_BITABLE_FIELD_TITLE=标题
FEISHU_BITABLE_FIELD_URL=文档链接
```

---

## 测试数据

你可以使用以下测试数据进行验证：

| 字段 | 示例值 |
|-----|-------|
| session_id | `test-001`, `test-002`... |
| topic | `季度工作总结`、`产品推广方案`、`会议纪要`... |
| document_type | `general`, `plan`, `report`, `memo`, `meeting` |
| tone | `formal`, `casual`, `friendly` |
| length | `short`, `medium`, `long` |
