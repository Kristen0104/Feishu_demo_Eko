# 飞书 Demo Eko

飞书 Demo Eko 是一个前后端一体的工作台演示项目。前端使用 Next.js，后端使用 FastAPI，包含飞书登录与集成、文档工作区、智能体会话、RAG 相关服务、团队与工作区接口，以及 AI PPT 导出流程。

## 目录结构

```text
frontend/          Next.js 前端应用
backend/           FastAPI 后端应用与 Python 服务
vendor/ppt-master/ AI PPT 模块使用的内置 PPT 转换运行时
```

运行数据、生成的 PPT 文件、本地依赖、缓存、测试产物和内部计划文档均不保留在仓库中。

## 环境要求

- Node.js 20+
- Python 3.12+
- PostgreSQL，并启用 pgvector
- Redis

## 启动后端

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动前请根据实际环境修改 `backend/.env`，包括数据库、Redis、飞书、LLM 和 AI PPT 相关配置。

## 启动前端

```sh
cd frontend
npm install
npm run dev
```

前端开发服务默认运行在 `3002` 端口。

## 仓库约定

- 不提交 `.env`、`.env.local`、虚拟环境、`node_modules`、`.next`、`backend/storage`、`backend/runtime`、生成的 PPT 或媒体文件。
- 保留 `backend/.env.example`、包声明文件、lockfile、Docker 和基础配置文件，确保克隆后可以安装和启动。
- 清理后的仓库只保留根目录 `README.md` 作为项目文档。
