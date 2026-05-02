# Eko Workspace · Frontend

Next.js 应用，用于 Eko 工作空间（登录、会话列表、会话详情等）的前端演示与开发。

## 环境要求

- **Node.js**：建议 **20 LTS** 或与当前 `package.json` 中 Next.js 版本兼容的较新版本
- 包管理器：本仓库使用 **npm**（见 `package-lock.json`）

## 本地运行

在 `frontend` 目录下执行：

```bash
npm install
npm run dev
```

默认开发地址：<http://localhost:3002>（`npm run dev` 已固定端口；根路径 `/` 会重定向到 `/login`）。

启动前会通过脚本清理 `.next` 缓存，并**尝试结束占用 3002 端口的旧进程**（避免 `EADDRINUSE`）；若你已在别处占用该端口且不想被结束，请先改用其他端口或暂时注释 `package.json` 里 `predev` 中的 `free-dev-port` 步骤。

若需改用 **3000**：

```bash
npm run dev:3000
```

生产构建与启动：

```bash
npm run build
npm start
```

## 演示登录（Mock，非真实鉴权）

当前登录页为**前端模拟校验**，与后端联调后需替换为真实接口。开发/演示时可使用：

| 项目 | 值 |
|------|-----|
| 邮箱 | `sarah.chen@eko.ai` |
| 密码 | `12345678` |

邮箱需**完全一致**（不区分大小写，提交时会按小写比较）。  
若曾在浏览器中修改过 `localStorage` 的 `eko:mock-password`，则以浏览器中保存的密码为准；可清除站点数据后恢复为上述默认密码。

**保持登录**：

- **勾选**「保持登录状态」：登录成功后在当前浏览器中通过 `localStorage` 保存票据，**15 天内**再次打开一般无需重复输入（到期后需重新登录）。
- **不勾选**：仅将本次会话写在 `sessionStorage`，**关闭该标签页/窗口后**需重新输入账号密码；同一次浏览过程中刷新页面通常仍保持已登录。

**说明**：会话页等路由未做服务端鉴权拦截，直接输入 URL 也可进入；星标与筛选等仍由 `Zustand`（localStorage）演示持久化，与上述登录票据分开存储。

## 常用页面路径

| 路径 | 说明 |
|------|------|
| `/login` | 登录页 |
| `/login/register` | 创建账号（演示表单，未接后端注册接口） |
| `/sessions` | 会话列表 |
| `/sessions/meeting-confirmation` | 会话详情（示例） |
| `/sessions/weekly-marketing-summary` | 会话详情（示例） |
| `/sessions/q2-ads-review` | 会话详情（示例） |

## 代码与配置

- 模拟账号常量位于：`src/components/login/LoginPage.tsx`（`MOCK_EMAIL`、`DEFAULT_PASSWORD`）
- 全局状态（登录态、筛选、星标等）：`src/store/app-store.ts`

## 其他命令

```bash
npm run lint   # ESLint
```

---

本目录由 [create-next-app](https://nextjs.org/docs/app/api-reference/cli/create-next-app) 初始化，更多 Next.js 文档见 <https://nextjs.org/docs>。
