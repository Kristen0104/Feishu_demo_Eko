# 后端功能模块

这个目录是后端的功能边界。

## 模块职责

- `intent/` - 意图识别与分流。
- `auth/` - 飞书登录、会话 token、当前用户身份。
- `feishu/` - 飞书 token、群消息、卡片 API、多维表格适配。
- `rag/` - 文档入库、检索、知识库回流。
- `workspace/` - 创建者权限、锁、协作状态。
- `sync/` - Redis Pub/Sub、WebSocket 广播、实时事件。
- `ppt/` - PPT 生成、模板导入、`ppt-master` 对接。

## 协作约定

- 业务逻辑优先放在这里。
- `backend/app/services/` 只做薄编排，不承载核心业务。
- `backend/app/api/` 只负责把 HTTP 请求转成模块/服务调用。
- 如果某个功能还没完成，就在所属文件里保留 `TODO(PRD-...)` 注释。
