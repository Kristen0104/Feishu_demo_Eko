# 飞书 Demo Eko

飞书 Demo Eko 是一个前后端一体的工作台演示项目。前端使用 Next.js，后端使用 FastAPI，包含飞书登录与集成、文档工作区、智能体会话、RAG 相关服务、团队与工作区接口，以及 AI PPT 导出流程。

> Nexus Pilot: AI Agent 驱动的多端协同办公助手
>
> GitHub: [Kristen0104/Feishu_demo_Eko](https://github.com/Kristen0104/Feishu_demo_Eko)

## 文档

- [产品需求文档 (PRD.md)](PRD.md)
- [技术架构文档 (ARCHITECTURE.md)](ARCHITECTURE.md)
- [接口定义规范 (API.md)](API.md)
- [团队分工手册 (TEAM.md)](TEAM.md)

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

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Next.js 15, Zustand, Tldraw SDK, Framer Motion |
| 后端 | Python FastAPI, DeepSeek |
| 数据 | PostgreSQL 14+ (pgvector), Redis |
| 跨端 | Tauri (桌面), Capacitor (移动端) |

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

## 快速开始

```bash
docker-compose up
```
