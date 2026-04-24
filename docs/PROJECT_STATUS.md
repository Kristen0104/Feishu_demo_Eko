# Eko 项目状态文档

> 更新日期：2026-04-24

## 项目概述

**Eko** 是一个 AI Agent 办公助手后端服务，基于 FastAPI + PostgreSQL + Redis + 飞书集成。

## 已完成功能

### 1. 基础架构 ✅

| 组件 | 状态 | 说明 |
|------|------|------|
| FastAPI 服务 | ✅ | 主服务入口，支持 CORS、中间件 |
| PostgreSQL 连接 | ✅ | 异步 ORM (SQLAlchemy asyncpg) |
| Redis 连接 | ✅ | 缓存 + Pub/Sub 实时消息 |
| JWT 认证 | ✅ | Token 生成与验证 |
| 配置管理 | ✅ | 环境变量 / .env 支持 |

### 2. 数据库模型 ✅

- [x] `users` - 用户表
- [x] `sessions` - 会话表
- [x] `tasks` - 任务表
- [x] `canvas_elements` - 画布元素表
- [x] `canvas_snapshots` - 画布快照表
- [x] `rag_files` - RAG 文件表
- [x] `feishu_bitable_config` - 飞书多维表格配置表

### 3. 飞书集成 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| WebSocket 长连接 | ✅ | 使用 lark-oapi SDK 接收消息事件 |
| 消息接收 | ✅ | 群聊 @机器人 消息接收 |
| @mention 过滤 | ✅ | 自动过滤 @_user_X 标记 |
| 意图识别 | ✅ | DOC/PPT/SUMMARY/CHAT 四种意图 |
| HTTP Webhook | ⚠️ | 已实现但未启用（备用） |

**意图识别关键词：**
- `DOC`: 文档、文稿、方案、报告、撰写、word、生成文档...
- `PPT`: ppt、演示、汇报、幻灯片、生成ppt...
- `SUMMARY`: 总结、摘要、概括、提炼、汇总...
- `CHAT`: 默认闲聊意图

### 4. LLM 集成 ✅

| 供应商 | 状态 | 说明 |
|--------|------|------|
| 火山引擎 (Volcengine) | ✅ | 主要供应商，API 格式 OpenAI 兼容 |
| DeepSeek | ⚠️ | 配置存在但未激活 |

## API 路由

### 已实现可调用

| 路由 | 方法 | 状态 |
|------|------|------|
| `/system/ping` | GET | ✅ 健康检查 |
| `/system/check-db` | GET | ✅ 数据库连接检查 |
| `/system/check-redis` | GET | ✅ Redis 连接检查 |
| `/hello` | GET | ✅ Hello World |
| `/api/v1/agent/execute` | POST | ✅ Agent 执行入口 |
| `/api/v1/agent/stop` | POST | ✅ Agent 停止 |
| `/api/v1/agent/history` | GET | ✅ 任务历史 |

### 待实现 (501)

| 路由 | 说明 |
|------|------|
| `/api/v1/auth/*` | 飞书 OAuth 登录 |
| `/api/v1/sessions/*` | 会话 CRUD |
| `/api/v1/rag/*` | RAG 文件管理 |
| `/api/v1/canvas/*` | 白板协作 |
| `/api/v1/settings/*` | Bitable 配置 |

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── api/                 # API 路由
│   │   ├── auth.py          # 认证（待实现）
│   │   ├── sessions.py      # 会话（待实现）
│   │   ├── rag.py           # RAG（待实现）
│   │   ├── agent.py         # Agent 执行
│   │   ├── canvas.py        # 白板（待实现）
│   │   ├── settings.py      # 设置（待实现）
│   │   └── webhook.py       # 飞书回调
│   ├── core/                # 核心组件
│   │   ├── database.py      # PostgreSQL
│   │   ├── redis_client.py  # Redis
│   │   ├── security.py      # JWT
│   │   └── state_machine.py # Agent 状态机
│   ├── models/              # SQLAlchemy 模型
│   │   └── models.py
│   ├── schemas/             # Pydantic schemas
│   │   └── schemas.py
│   ├── services/           # 业务服务
│   │   ├── feishu_service.py   # 飞书 API
│   │   ├── intent_service.py   # 意图识别
│   │   └── llm_service.py      # LLM 调用
│   └── feishu_ws.py         # 飞书 WebSocket 长连接
├── docs/
│   ├── PROJECT_STATUS.md    # 本文档
│   └── redis_structure.md   # Redis 结构文档
├── .env                     # 环境配置（不上传）
├── requirements.txt         # Python 依赖
└── Dockerfile               # Docker 部署
```

## 环境变量

```bash
# 数据库
POSTGRES_USER=postgres
POSTGRES_PASSWORD=G1105540105g
POSTGRES_HOST=39.104.87.235
POSTGRES_PORT=5432
POSTGRES_DB=nexus_pilot

# Redis
REDIS_HOST=39.104.87.235
REDIS_PORT=6379
REDIS_PASSWORD=123456

# 飞书
FEISHU_APP_ID=cli_a9619dc3b0b99cef
FEISHU_APP_SECRET=tZbyh7ej2lXBIW6Hp0ktHgkFnmuKUMZM

# LLM (火山引擎)
VOLCENGINE_API_KEY=ark-68e0d61c-2646-4a0e-8ac1-7ea35da99d21-a6c8f
VOLCENGINE_MODEL=ep-20260423222610-xbx2l
```

## 下一步计划

1. 完成会话管理 API (sessions)
2. 实现 RAG 文件上传和向量搜索
3. 集成实际文档生成（DOC/PPT）
4. 前端对接

## 启动方式

```bash
cd backend
source .venv/bin/activate
python -m app.main
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动飞书 WebSocket 长连接（单独进程）
python app/feishu_ws.py
```