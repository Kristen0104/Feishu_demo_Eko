# 飞书 Demo Eko

Eko 是一个面向飞书生态的 AI 原生办公工作台演示项目。项目由 Next.js 前端工作台、FastAPI 后端、飞书集成、Agent 编排、RAG 检索、Bitable 结构化数据、Redis 实时事件总线，以及 AI PPT / 文档 / 画板生成能力组成。

这个仓库用于演示一条完整的办公流：用户可以在飞书群里 @Eko，也可以进入网页工作台发起任务；系统会识别意图、检索上下文、调用合适工具、实时展示进度，并将结果回流到飞书生态。

## 核心能力

- 飞书 OAuth 登录、事件回调处理和长连接监听。
- Agent 对话，支持 chat、文档、PPT、画板等工具级意图路由。
- 基于 LangGraph 的 ReAct 运行时，负责上下文装载、意图路由、澄清中断、检索和工具执行。
- RAG 知识库，支持文件入库、Embedding 向量化和 pgvector 相似度检索。
- Bitable OpenAPI 集成，支持结构化数据检索和产物归档。
- AI PPT 生成与编辑，使用内置 `vendor/ppt-master` 运行时。
- 文档生成、飞书文档同步、tldraw / 飞书画板工作流。
- Redis Pub/Sub 实时总线，用于 Agent 进度、Session 状态和同步结果广播。
- Next.js 工作台，包含会话、知识库、文档、团队、设置、个人中心等页面。

## 技术架构

```text
飞书群 / 飞书卡片 / Web 工作台
        |
        v
Next.js 前端  <---- 实时 Session 事件 ---->  FastAPI 后端
                                             |
                                             v
                         RouterAgent -> AgentRuntime -> Tool Registry
                              |           |              |
                              |           v              v
                              |       RAG / Bitable   Tool Adapters
                              |                          |
                              v                          v
                    Document / AIPPT / Canvas / Sync / Archive
                                             |
                                             v
                         PostgreSQL + pgvector、Redis、Feishu OpenAPI
```

Agent 单轮任务的运行链路是：

```text
context_load -> intent_route -> clarification_gate -> observe/retrieve -> act/tool -> observe_tool -> final
```

RAG 检索当前使用 Embedding + pgvector cosine distance 排序。Agent 链路中默认取 RAG Top-4 和 Bitable Top-4，合并后最多保留 8 条上下文进入 Planner 和工具调用。当前没有引入独立 reranker 模型。

## 目录结构

```text
backend/           FastAPI 后端、Agent、飞书、Bitable、RAG、AIPPT 模块
frontend/          Next.js 前端工作台
docs/              集成说明和答辩材料
vendor/ppt-master/ AI PPT 模块使用的内置转换运行时
API.md             API 接口定义草案
ARCHITECTURE.md    架构说明
PRD.md             产品需求说明
TEAM.md            团队说明
```

运行数据、生成的 PPT 文件、本地依赖、缓存、上传文件和临时输出均不保留在仓库中。

## 环境要求

- Node.js 20+
- Python 3.12+
- PostgreSQL 14+，并启用 pgvector
- Redis 7+
- 如需联调真实飞书能力，需要配置飞书应用凭证和相关权限

## 后端启动

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

启动前请修改 `backend/.env`。重点配置项包括：

- PostgreSQL 和 Redis 连接信息。
- 飞书应用凭证、OAuth 回调和事件配置。
- Agent 模型与 Embedding 模型配置。
- Bitable 开关、归档开关和默认工作区配置。
- AI PPT 模型、存储目录、队列和图片生成配置。

启动后端服务：

```sh
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端接口基础路径为 `/api/v1`。在配置静态目录后，后端也可以挂载前端构建产物。

## 前端启动

```sh
cd frontend
npm install
npm run dev
```

前端开发服务默认运行在 `3002` 端口。

也可以在仓库根目录执行：

```sh
npm run dev
npm run build
npm run start
npm run lint
```

根目录脚本会转发到 `frontend` 包执行。

## 关键配置

### Agent 与 RAG

```env
AGENT_MODEL=deepseek-v4-flash
AGENT_API_BASE=https://api.deepseek.com
AGENT_EMBEDDING_MODEL=Qwen3-Embedding-8B
AGENT_EMBEDDING_API_BASE=https://ai.gitee.com/v1
RAG_EMBEDDING_DIMENSIONS=1024
RAG_CHUNK_SIZE=450
RAG_CHUNK_OVERLAP=80
```

如果没有配置有效的 Embedding API Key，后端会使用确定性的本地 Embedding 客户端，便于测试和无 Key 开发。

### Bitable

```env
BITABLE_ENABLED=true
BITABLE_ARCHIVE_ENABLED=false
BITABLE_DEFAULT_WORKSPACE_ID=Feishu_demo_Eko
BITABLE_QUERY_LIMIT=8
```

Bitable 有两个角色：一是作为 Agent 生成时的结构化上下文来源，二是作为文档、PPT、画板等完成产物的可选归档目标。详细说明见 `docs/bitable-openapi-integration.md`。

### Redis

Redis 既是基础设施依赖，也是实时事件总线。后端会通过 Redis 相关流程发布 Agent 进度、Session 状态、飞书同步状态和 AI PPT 队列信息。

```env
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### AI PPT

```env
AIPPT_MODEL=deepseek-v4-flash
AIPPT_STORAGE_DIR=storage/aippt
AIPPT_VENDOR_DIR=vendor/ppt-master
AIPPT_REDIS_QUEUE_ENABLED=true
```

生成文件和中间 PPT 工程默认存储在 `backend/storage/aippt`，不应提交到仓库。

## 测试与检查

运行后端测试：

```sh
cd backend
python -m pytest
```

运行常用冒烟测试：

```sh
cd backend
python -m pytest \
  tests/test_agent_intent_routing.py \
  tests/test_agent_event_channels.py \
  tests/test_bitable_service.py \
  tests/test_feishu_full_flow.py
```

检查 Python 导入和编译：

```sh
cd backend
python -m compileall app
```

运行前端检查：

```sh
cd frontend
npm run lint
npm run build
```

## 开发提示

- `frontend/src/components/knowledge/BitableSourcesPanel.tsx`：Bitable 数据源配置 UI。
- `backend/app/modules/agent/service.py`：意图路由、当前产物判断和 Agent 主执行流程。
- `backend/app/modules/agent/runtime.py`：基于 LangGraph 的 Agent Runtime。
- `backend/app/modules/rag/`：Embedding、文件入库、切分和 pgvector 检索。
- `backend/app/modules/bitable/`：飞书 Bitable OpenAPI 集成。
- `backend/app/modules/aippt/`：AI PPT 任务创建、渲染和导出。
- `backend/app/modules/sync/`：Session 状态同步和实时事件管理。

## 仓库约定

不要提交：

- `.env`、`.env.local`、密钥、凭证和本地隧道地址。
- Python 虚拟环境、`node_modules`、`.next`、缓存和测试产物。
- `backend/storage`、`backend/runtime`、上传文件、生成的 PPT 和媒体文件。
- 临时截图、本地调试导出和机器相关文件。

应保留：

- 源码、测试、包声明、lockfile、`.env.example`、文档和可复用脚本。

## 相关文档

- `API.md`
- `ARCHITECTURE.md`
- `PRD.md`
- `docs/bitable-openapi-integration.md`
