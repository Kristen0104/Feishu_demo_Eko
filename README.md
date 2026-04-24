# Eko - 飞书AI校园挑战赛作品

> Nexus Pilot: AI Agent 驱动的多端协同办公助手

## 项目简介

Eko 是一款基于 AI Agent 驱动的多端协同办公助手。它作为工作流的"主驾驶 (Pilot)"，通过识别用户意图，自动决定是生成 Word 文稿、PPT 画布，还是仅进行即时闲聊回复，实现三端实时同步与飞书生态闭环。

## 文档

- [产品需求文档 (PRD.md)](PRD.md)
- [技术架构文档 (ARCHITECTURE.md)](ARCHITECTURE.md)

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Next.js 15, Zustand, Tldraw SDK, Framer Motion |
| 后端 | Python FastAPI, DeepSeek |
| 数据 | PostgreSQL 14+ (pgvector), Redis |
| 跨端 | Tauri (桌面), Capacitor (移动端) |

## 快速开始

```bash
# 开发环境启动
docker-compose up
```

