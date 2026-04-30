# HTML PPT 生成与 PPTX 导出系统设计

## 目标

本阶段实现一个可测试、可扩展的 PPT 生成后端模块和极简前端测试页。用户输入文本或聊天记录后，系统生成结构化 PPT JSON、渲染为 HTML 幻灯片，并支持导出 PPTX。系统支持自然语言二次修改、多主题模板和增量更新；多人协作只预留字段，不实现实时协作；智能图片匹配暂不实现。

## 架构

系统以 JSON 中间层为核心，而不是让模型直接输出不可控的完整 HTML。后端负责生成和维护 deck 数据，HTML 预览和 PPTX 导出都从同一份 deck JSON 派生。

数据链路：

```text
前端测试页 -> /api/v1/ppt/decks -> LLM 或 fallback 生成 deck JSON
           -> 后端渲染 HTML -> 前端预览
           -> /api/v1/ppt/decks/{deck_id}/modify -> 更新 deck JSON 与 HTML
           -> /api/v1/ppt/decks/{deck_id}/export -> 生成 PPTX 文件
```

## 后端模块

新增 `backend/app/modules/ppt`，保持现有 FastAPI 模块风格：

- `schemas.py` 定义请求、slide、deck、export、theme 的 Pydantic 契约。
- `service.py` 负责生成、修改、HTML 渲染、导出调度和内存态 deck 管理。
- `router.py` 暴露 `/api/v1/ppt` 下的 REST API。
- `dependencies.py` 提供服务依赖。

第一阶段使用内存仓储，便于比赛 demo 和测试；后续可替换为数据库或 Redis，不改变 API 契约。

## API 契约

- `GET /api/v1/ppt/themes`：返回 `科技风`、`商务风`、`简约风`。
- `POST /api/v1/ppt/decks`：输入 `type`、`content`、`preferences`，返回完整 deck、HTML、版本和历史。
- `POST /api/v1/ppt/decks/{deck_id}/modify`：输入自然语言 `instruction`，可带 `slide_id` 和 `current_deck`，返回更新后的 deck。
- `POST /api/v1/ppt/decks/{deck_id}/export`：从当前 deck 导出 PPTX，返回文件路径和下载 URL。

所有接口使用现有 `ApiResponse` 包装。

## 数据模型

Deck 包含：

- `deck_id`
- `title`
- `theme`
- `slides`
- `html`
- `version`
- `history`
- `author`
- `last_modified`

试验版的 slide schema 额外支持 `layout` 字段，用来约束版式意图。当前允许的 layout 值包括 `cover`、`bullets`、`two_column`、`timeline`、`metrics`、`summary`。联测时应优先覆盖这些布局，确保封面、指标、时间线、风险对比和行动总结都能在预览里清楚区分。

后续预期新增的 layout 包括 `section_divider`、`quote`、`comparison`、`process`、`matrix`、`architecture`。文档侧先按下面的字段约定对齐，便于前端测试页直接构造联测样例：

- `section_divider`：`title`、`subtitle`、`section`、`accent`、`notes`
- `quote`：`quote`、`author`、`context`、`notes`
- `comparison`：`left_title`、`right_title`、`left_items`、`right_items`、`summary`、`notes`
- `process`：`title`、`steps`、`inputs`、`outputs`、`notes`
- `matrix`：`title`、`quadrants`、`axis_x`、`axis_y`、`highlights`、`notes`
- `architecture`：`title`、`modules`、`layers`、`links`、`notes`

Slide 包含：

- `id`
- `title`
- `body`
- `images`
- `notes`
- `theme`
- `author`
- `last_modified`
- `version`

`author`、`version`、`last_modified` 是多人协作预留字段。每次修改相关 slide 时，slide `version + 1`，deck `version + 1`，并记录 history。

## DeepSeek 调用

后端调用现有 `LlmClient.complete_json`，使用 DeepSeek 兼容接口和 `deepseek-v4-flash` 模型，要求模型返回符合 schema 的 JSON。服务端负责归一化字段、限制页数（`1-20`）、补齐缺省值。

PPT 生成与自然语言修改必须配置 `AGENT_API_KEY`。未配置时接口返回 `503`，不再使用本地内容 fallback。

## HTML 渲染

HTML 渲染由后端从 deck JSON 生成。每页使用 `<section class="ppt-slide">`，包含标题、正文和备注数据。主题通过内联 CSS 控制，三套主题只改变颜色、字体层级和背景，不改变数据结构。

前端只展示后端返回的 HTML，不承担业务渲染逻辑。

## PPTX 导出

优先复用 `pptxgenjs`，从 deck JSON 直接生成 PPTX。同步导出到 `GENERATED_ROOT/ppt/decks/<deck_id>/deck.pptx`，返回：

- `status`
- `pptx_path`
- `download_url`
- `slide_count`

如果本机 Node 依赖缺失，导出接口应返回清晰错误；单元测试可通过生成文件存在性或服务封装替身验证契约。

## 前端测试页

前端仅用于开发验证：

- 文本/聊天记录输入框。
- 主题选择和页数输入。
- 生成按钮。
- HTML PPT 预览区域。
- 自然语言修改输入和可选 slide id。
- 导出按钮与结果展示。

页面不做产品化导航、账号体系或复杂状态管理。

## 非目标

- 不实现多人实时协作。
- 不做智能图片匹配。
- 不做复杂模板市场。
- 不把前端做成正式产品页。

## 验收

- 路由注册测试包含 `/api/v1/ppt` 关键接口。
- 未配置 DeepSeek 时，生成与修改接口返回清晰 `503`。
- 配置 DeepSeek 时，生成与修改使用模型返回的 JSON 生成 deck 和 HTML。
- 修改接口能更新指定 slide 的标题或内容，并递增版本。
- 主题切换能反映到 deck 和 HTML。
- 导出接口返回明确的 PPTX 元数据。
- 前端测试页能调用生成、修改、导出接口并刷新预览。
