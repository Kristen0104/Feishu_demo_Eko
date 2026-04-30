# Feishu_demo_Eko
2026飞书AI校园挑战赛小组作品

## AI PPT Module

项目现在包含一个可运行的 `aippt` 后端模块，职责是：

- FastAPI 接收主题文本、URL 或文件输入
- 调用 `DeepSeek V4 Flash` 生成 PPT 大纲、`design_spec.md`、每页 SVG 和讲稿 notes
- 提供 `design_mode=template|free_design` 两条隔离生成逻辑，默认不影响传统模板效果
- 调用 `vendor/ppt-master` 的官方脚本链把 SVG 编译成可编辑 `.pptx`
- 通过 `Celery + Redis` 异步执行长任务
- 用本地 `storage/` 保存上传文件、项目目录和最终导出文件

核心接口：

- `POST /api/v1/ppt/generate`
- `GET /api/v1/ppt/jobs/{job_id}`
- `GET /api/v1/ppt/files/{job_id}`

## AI PPT Setup

1. 配置 `backend/.env`：

```env
AIPPT_MODEL=deepseek-v4-flash
AIPPT_API_BASE=https://api.deepseek.com
AIPPT_API_KEY=your_deepseek_api_key
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
AIPPT_REDIS_QUEUE_ENABLED=true
AIPPT_SLIDE_CONCURRENCY=2
AIPPT_THINKING_ENABLED=false
AIPPT_IMAGE_GENERATION_ENABLED=false
AIPPT_IMAGE_API_BASE=https://www.packyapi.com
AIPPT_IMAGE_API_KEY=your_sora_group_token
AIPPT_IMAGE_MODEL=gpt-image-2
AIPPT_IMAGE_SIZE=3840x2160
AIPPT_IMAGE_QUALITY=high
AIPPT_IMAGE_OUTPUT_FORMAT=png
```

2. 安装后端依赖：

```bash
cd backend
pip install -r requirements.txt
```

3. 安装 `ppt-master` 导出依赖：

```bash
pip install -r ../vendor/ppt-master/requirements.txt
```

4. 启动 Redis。

5. 启动 FastAPI：

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

6. 启动 Celery worker：

```bash
cd backend
celery -A app.core.celery_app.celery_app worker -Q aippt -l info
```

7. 提交主题生成任务：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/ppt/generate \
  -H 'Content-Type: application/json' \
  -d '{"topic":"AI 生成 PPT 系统设计","page_count":6,"style":"clean_business","design_mode":"template"}'
```

需要更高自由度页面时，显式选择自由设计逻辑：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/ppt/generate \
  -H 'Content-Type: application/json' \
  -d '{"topic":"一线客服团队 AI 协同工作台建设方案","page_count":6,"style":"cinematic_tech","design_mode":"free_design"}'
```

8. 提交文件任务：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/ppt/generate \
  -F "file=@/absolute/path/to/report.pdf" \
  -F "page_count=6" \
  -F "style=clean_business" \
  -F "design_mode=template"
```

运行产物会写到：

- `backend/storage/aippt/jobs/`
- `backend/storage/aippt/uploads/`
- `backend/storage/aippt/projects/`
- `backend/storage/aippt/exports/`

## AI PPT Pipeline

当前后端按下面这条链路工作：

```text
FastAPI
  -> Celery / Redis
  -> FileParser
  -> LLM Service
  -> storage/projects/<job_id>
  -> PPT Master scripts
  -> storage/exports/<job_id>.pptx
```
