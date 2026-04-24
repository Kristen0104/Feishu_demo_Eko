# 开发者测试指南

> 本指南帮助另一位开发者快速上手测试 Eko 后端功能

---

## 一、环境准备

### 1.1 克隆项目

```bash
git clone <repo-url>
cd Feishu_demo_Eko
```

### 1.2 安装依赖

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 1.3 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

**必需配置：**
```bash
# 数据库
POSTGRES_USER=postgres
POSTGRES_PASSWORD=你的密码
POSTGRES_HOST=39.104.87.235
POSTGRES_PORT=5432
POSTGRES_DB=eko

# Redis
REDIS_HOST=39.104.87.235
REDIS_PORT=6379
REDIS_PASSWORD=123456

# 飞书
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx

# LLM
VOLCENGINE_API_KEY=ark-xxx
VOLCENGINE_MODEL=ep-20260423222610-xbx2l
```

---

## 二、快速测试

### 2.1 启动后端服务

```bash
cd backend
source .venv/bin/activate
python -m app.main
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问：`http://localhost:8000/docs` 查看 API 文档

### 2.2 健康检查

```bash
curl http://localhost:8000/system/ping
# 预期返回: {"status":"ok","timestamp":"..."}
```

### 2.3 检查数据库连接

```bash
curl http://localhost:8000/system/check-db
# 预期: {"status":"ok","postgres":"connected"}
```

### 2.4 检查 Redis 连接

```bash
curl http://localhost:8000/system/check-redis
# 预期: {"status":"ok","redis":"connected"}
```

---

## 三、飞书集成测试

### 3.1 启动 WebSocket 长连接

```bash
# 新开一个终端
cd backend
source .venv/bin/activate
python app/feishu_ws.py
```

日志输出到控制台或 `/tmp/feishu_ws.log`

### 3.2 测试消息接收

1. 在飞书群中 @机器人 发送消息
2. 观察 `feishu_ws.py` 日志输出
3. 预期看到：
   ```
   [ Handler called ]
   [ Intent ]: CHAT, [ Text ]: 你的消息内容
   [ ChatID ]: oc_xxx, [ MessageID ]: om_xxx
   ```

### 3.3 测试意图识别

发送以下关键词测试：

| 关键词 | 预期意图 |
|--------|----------|
| "帮我写个文档" | DOC |
| "做一个PPT" | PPT |
| "总结一下" | SUMMARY |
| "你好" | CHAT |

---

## 四、用 Claude Code 写测试

### 4.1 基本方法

在项目目录下启动 Claude Code：

```bash
cd Feishu_demo_Eko
claude
```

### 4.2 常用测试 Prompt 模板

**测试 API 接口：**
```
帮我写一个测试脚本，测试 /api/v1/agent/execute 接口
请求体：{"session_id": "test-session", "message": "你好"}
验证返回的 intent 和 result 字段
```

**测试意图识别：**
```
测试 intent_service.py 的 recognize_intent 函数
测试用例：
- "帮我写个文档" -> DOC
- "做个PPT" -> PPT
- "你好" -> CHAT
```

**测试数据库模型：**
```
写一个测试验证 Session 模型可以正确创建和查询
```

**测试飞书消息解析：**
```
测试 parse_message_content 函数
输入：{"content": "{\"text\":\"@_user_1 测试消息\"}"}
预期输出：测试消息（已过滤 @mention）
```

### 4.3 运行测试

```bash
# 运行单个测试文件
python -m pytest tests/test_intent.py -v

# 或直接运行
python tests/test_intent.py
```

---

## 五、调试技巧

### 5.1 查看详细日志

`feishu_ws.py` 使用 `lark.LogLevel.DEBUG` 可看到完整的消息 payload

### 5.2 打印中间变量

在 `feishu_ws.py` handler 中添加：
```python
print(f"[ Debug ]: {变量名}", flush=True)
```

### 5.3 断点调试

```python
import pdb; pdb.set_trace()
```

### 5.4 常见问题

| 问题 | 解决方案 |
|------|----------|
| `ModuleNotFoundError: No module named 'app'` | 确保从 backend 目录运行，或设置 `PYTHONPATH=.` |
| WebSocket 连接失败 | 检查网络和飞书配置 |
| 消息收到但不触发 handler | 检查事件订阅是否开启 |
| 数据库连接失败 | 检查 PostgreSQL 是否可用 |

---

## 六、测试飞书消息接收的 Claude Prompt

```
帮我验证飞书 WebSocket 长连接功能：
1. 检查 feishu_ws.py 的 handler 是否正确注册
2. 模拟一条飞书消息事件输入
3. 验证 parse_message_content 能正确解析文本消息
4. 验证 recognize_intent 能正确识别 DOC/PPT/SUMMARY/CHAT 意图

消息样例 payload：
{"event": {"message": {"message_type": "text", "content": "{\"text\":\"@_user_1 测试\"}"}}}
```