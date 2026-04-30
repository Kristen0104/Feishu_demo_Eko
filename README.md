# Feishu_demo_Eko

2026 飞书 AI 校园挑战赛小组作品。

## 快速启动

后端配置模板在 `backend/.env.example`。拉取项目后复制一份到 `backend/.env`，填好飞书、LLM、AIPPT 等 API Key 即可运行；PostgreSQL 和 Redis 默认指向远端 `<YOUR_SERVER_IP>`。

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
npm install
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端静态调试页在 `frontend/`，后端启动后默认挂载到 `/frontend`。

## 配置与提交约定

- 提交配置模板：`backend/.env.example`
- 不提交真实密钥：`backend/.env`、根目录 `.env`
- 不提交运行产物：`backend/storage/`、`backend/dump.rdb`、`frontend/dist/`、缓存目录
- 大型 PPT 运行产物由服务运行时重新生成

## 常用验证

```bash
cd backend
.venv/bin/python -m pytest -q -k 'not login'
node --test tests/services/test_export_deck_to_pptx.mjs
```
