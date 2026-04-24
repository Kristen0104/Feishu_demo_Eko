# Eko Redis 结构文档

## 1. 连接信息
- Host: 39.104.87.235
- Port: 6379
- Password: 123456
- DB: 0

---

## 2. Key 设计

### 2.1 会话上下文缓存 (Cache)
```
Key: session:{session_id}:context
Type: String (JSON)
TTL: 300秒 (5分钟)
内容: 最近5轮对话历史
[
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "..."}
]
```

### 2.2 Agent 状态 (State)
```
Key: session:{session_id}:agent_state
Type: String
TTL: 无 (随会话结束删除)
内容: IDLE|ANALYZING|RETRIEVING|GENERATING|SYNCING|COMPLETED
```

### 2.3 任务进度 (Task Progress)
```
Key: task:{task_id}:progress
Type: Hash
TTL: 3600秒 (1小时)
内容:
  - status: pending|running|completed|failed
  - current_step: 1
  - total_steps: 5
  - result_url: "..."
```

---

## 3. Pub/Sub 频道

### 3.1 全局广播频道
```
Channel: nexus:broadcast
用途: 所有客户端订阅，广播系统级消息
消息格式: {"type": "...", "payload": {...}}
```

### 3.2 会话专属频道
```
Channel: session:{session_id}
用途: 该会话下的实时更新 (元素变更、任务状态)
消息格式: {"type": "...", "payload": {...}}

type 类型:
- INTENT_RECOGNIZED: {"intent": "CHAT"|"DOC"|"PPT"}
- AGENT_PLANNING: {"steps": [...]}
- DOC_STREAM: {"chunk": "..."}
- CANVAS_UPDATE: {"upsert": [], "delete": []}
- TASK_COMPLETED: {"result_url": "", "bitable_id": ""}
- CURSOR_SYNC: {"user_id": "", "x": 0, "y": 0}
```

### 3.3 用户专属频道
```
Channel: user:{user_id}
用途: 用户私人消息 (通知、提醒)
```

---

## 4. 示例代码

### 发布消息
```python
await redis_client.publish(f"session:{session_id}", json.dumps({"type": "CANVAS_UPDATE", "payload": {...}}))
```

### 订阅消息
```python
pubsub = redis_client.pubsub()
await pubsub.subscribe(f"session:{session_id}")
async for message in pubsub.listen():
    data = json.loads(message["data"])
```

### 缓存对话上下文
```python
# 获取
context = await redis_client.get(f"session:{session_id}:context")
# 设置
await redis_client.setex(f"session:{session_id}:context", 300, json.dumps(context))
```

---

## 5. 清理策略
- Session context: 会话空闲5分钟后过期
- Task progress: 任务完成后1小时删除
- Agent state: 随 session 删除
