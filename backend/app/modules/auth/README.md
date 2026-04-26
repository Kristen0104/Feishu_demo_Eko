# Auth 模块

这个模块负责飞书登录和后端会话身份，不负责前端 UI。

## 职责

- 飞书用户登录
- 用户信息写入 `users` 表
- 后端签发和校验自己的访问 token
- 获取当前登录用户

## 路由

- `POST /api/v1/auth/feishu/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

## 当前实现

- 现在登录入口先以 `feishu_open_id` 为主键进行用户创建/更新。
- 后续如果要接 Feishu OAuth code exchange，可以在这个模块里继续扩展，不需要改其他业务模块。

