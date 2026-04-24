# Eko 初始开发计划 (仅后端代码框架 + 中间件配置)

## 项目概览
- **产品**: Eko - AI Agent 驱动的多端协同办公助手
- **周期**: 4.24 - 5.14 (Demo: 5.06)
- **团队**: A(前端), B(后端/AI), C(架构/同步)
- **分工**: 本项目仅涉及**后端**，前端由他人负责

---

## 阶段一：后端项目结构初始化

### 1.1 后端目录结构
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py          # /auth 路由
│   │   ├── sessions.py      # /sessions 路由
│   │   ├── rag.py           # /rag 路由
│   │   ├── agent.py         # /agent 路由
│   │   ├── canvas.py        # /canvas 路由
│   │   ├── settings.py      # /settings 路由
│   │   └── webhook.py       # /webhook 路由
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── task.py
│   │   ├── canvas.py
│   │   └── rag_file.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── agent_service.py
│   │   ├── rag_service.py
│   │   └── canvas_service.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py     # PostgreSQL/SQLAlchemy
│   │   ├── redis_client.py  # Redis 连接
│   │   ├── security.py     # JWT/认证
│   │   └── state_machine.py # Agent 状态机
│   └── schemas/
│       ├── __init__.py
│       └── schemas.py       # Pydantic 模型
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 阶段二：后端中间件配置

### 2.1 核心依赖
- FastAPI + Uvicorn
- SQLAlchemy 2.0 + asyncpg
- pgvector (向量存储)
- Redis (aioredis)
- Pydantic v2
- python-jose (JWT)
- python-multipart (文件上传)

### 2.2 中间件配置
- [ ] CORS 中间件 (允许前端跨域)
- [ ] JWT 认证中间件
- [ ] Redis 连接池 (Pub/Sub + Cache)
- [ ] PostgreSQL 连接池
- [ ] WebSocket 依赖注入
- [ ] 请求日志中间件
- [ ] 错误处理中间件

### 2.3 数据库模型
- [ ] User (用户表)
- [ ] Session (会话表)
- [ ] Task (任务表，含状态机)
- [ ] CanvasElement (画布元素)
- [ ] RagFile (知识库文件)

---

## 阶段三：Docker 环境配置

### 3.1 docker-compose.yml
- [ ] FastAPI 服务
- [ ] PostgreSQL + pgvector 镜像
- [ ] Redis 镜像

---

## 里程碑检查点

| 阶段 | 完成标志 |
|-----|---------|
| 项目初始化 | backend/ 目录结构完整 |
| 后端中间件 | FastAPI 启动成功，Redis/Postgres 连接正常 |
| Docker | `docker-compose up` 一键启动 |

---

## 依赖关系
```
阶段一 ──► 阶段二 ──► 阶段三
   │           │           │
   └── 目录结构 └── 中间件配置 └── Docker环境
```
