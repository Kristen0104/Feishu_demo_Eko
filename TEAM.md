# Eko 团队分工与协作手册

**日期**：2026-04-24

---

## 团队角色与职责

### 成员 A：前端开发

| 模块 | 具体任务 |
|------|----------|
| **项目初始化** | Next.js 15 项目搭建、目录结构设计、依赖安装 |
| **Dashboard** | 会话列表页、会话详情页、登录页 |
| **Tldraw 画布** | 集成 Tldraw SDK、实现画布自动渲染、生长动效 |
| **Word 预览** | Markdown 渲染、实时流式更新展示 |
| **状态管理** | Zustand store 设计、多端状态同步逻辑 |
| **WebSocket** | 实时消息订阅、状态机更新 UI |
| **Framer Motion** | Agent 思考动画、元素入场动效 |
| **三端适配** | 响应式布局、Tauri/Capacitor 集成调试 |

---

### 成员 B：后端开发

| 模块 | 具体任务 |
|------|----------|
| **项目初始化** | FastAPI 项目搭建、SQLAlchemy 模型定义 |
| **Auth API** | 飞书登录、JWT 鉴权中间件 |
| **Sessions API** | 会话 CRUD、上下文管理 |
| **RAG 模块** | pypdf/docx2txt 解析、Embedding 调用、pgvector 检索 |
| **Canvas API** | 快照存储、版本管理、增量更新 |
| **飞书集成** | Bitable 配置、Webhook 接收、飞书 API 封装 |
| **Redis 集成** | Pub/Sub 广播、对话缓存 |
| **部署** | Docker Compose、生产环境配置 |

---

### 成员 C：

| 阶段 | 具体任务 |
|------|----------|
| **Prompt 体系** | 意图分类 Prompt、Word 生成 Prompt、PPT 布局 Prompt、Function Calling 定义 |
| **Agent 逻辑** | 状态机流程设计、任务拆解逻辑、Prompt 调优 |
| **RAG 调优** | 测试文档准备、分片策略实验、Bad Case 分析、检索效果评估 |
| **Demo 设计** | 演示脚本撰写、录屏剪辑、答辩 PPT 制作 |
| **产品细节** | UI 文案、空状态设计、错误提示、动效建议 |
| **测试验收** | 全流程测试、Issue 记录、体验反馈 |
| **文档** | PRD 维护、演示场景设计 |

---

## 开发里程碑

### 4.24-4.27 - 架子搭建

| 成员 | 目标 |
|------|------|
| A | Next.js 项目跑通、基础页面布局 |
| B | FastAPI 项目跑通、数据库表设计 |
| C | 意图分类 Prompt 验证、测试用例 |

### 4.27-5.3 - 核心功能

| 成员 | 目标 |
|------|------|
| A | Tldraw 集成、Word 预览、WebSocket 连接 |
| B | RAG 模块、Agent 执行接口、Redis 集成 |
| C | Word/PPT 生成 Prompt、知识库测试数据准备 |

### 5.4-5.6 - 体验优化

| 成员 | 目标 |
|------|------|
| A | 动效、三端适配 |
| B | 飞书集成、部署 |
| C | 全流程调优、Demo 视频录制 |

---

## 协作方式

- **每日站会**：同步进度、同步阻塞
- **GitHub Issues**：任务拆分、Bug 跟踪
- **共同调试**：Prompt 效果需要三人一起测试

---

## 相关文档

- [PRD.md](PRD.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)
