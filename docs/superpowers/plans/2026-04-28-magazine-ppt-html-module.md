# 杂志风 HTML PPT 模块实施计划

> **给执行型 agent 的要求：** 推荐使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务逐项执行。文档使用 `- [ ]` 复选框跟踪进度。

**目标：** 新增一个独立的后端 `ppt` 模块，原样 vendoring `guizang-ppt-skill` 的规则和模板资产，复用现有 LLM 客户端生成单文件 HTML deck，保存产物文件，并暴露任务查询与预览接口，且不复用飞书 `board` 流程。

**方案：** 该能力与 `canvas/board` 完全隔离。后端接收 PPT 生成任务后，从仓库内加载 vendored 的 prompt / template / rule 资产，让模型一次性输出完整 HTML 文档；随后服务端做轻量校验，保存为 `index.html`，并提供任务状态与预览路由。第一期优先保证与上游 skill 的风格一致，不做重型结构化重写。

**技术栈：** FastAPI、Pydantic、pytest、pathlib、现有 `app.services.llm_client.LlmClient`、仓库内 vendored Markdown/HTML 资产、`backend/generated` 下的文件落盘。

---

## 一、建议文件结构

- 新建：`backend/app/modules/ppt/__init__.py`
- 新建：`backend/app/modules/ppt/router.py`
- 新建：`backend/app/modules/ppt/schemas.py`
- 新建：`backend/app/modules/ppt/repository.py`
- 新建：`backend/app/modules/ppt/service.py`
- 新建：`backend/app/modules/ppt/dependencies.py`
- 新建：`backend/app/services/ppt_html_generate_service.py`
- 新建：`backend/app/services/ppt_html_prompt_assets.py`
- 新建：`backend/app/services/ppt_html_validator.py`
- 新建：`backend/app/modules/ppt/assets/guizang/SKILL.md`
- 新建：`backend/app/modules/ppt/assets/guizang/template.html`
- 新建：`backend/app/modules/ppt/assets/guizang/references/layouts.md`
- 新建：`backend/app/modules/ppt/assets/guizang/references/themes.md`
- 新建：`backend/app/modules/ppt/assets/guizang/references/components.md`
- 新建：`backend/app/modules/ppt/assets/guizang/references/checklist.md`
- 新建：`backend/tests/modules/test_ppt_task_contract.py`
- 新建：`backend/tests/modules/test_ppt_prompt_assets.py`
- 新建：`backend/tests/modules/test_ppt_html_validator.py`
- 新建：`backend/tests/modules/test_ppt_generate_service.py`
- 修改：`backend/app/core/container.py`
- 修改：`backend/app/config.py`
- 修改：`backend/tests/modules/test_module_registration.py`
- 修改：`API.md`

## 二、必须保持的设计原则

- 这个模块不属于 `board`，不要往 `backend/app/services/board_generate_service.py` 里塞新逻辑。
- 上游 `guizang-ppt-skill` 内容应该以 vendoring 的方式引入，并保留来源与许可证信息，不要先手工改写成本地二创版本。
- 第一阶段按用户偏好，直接采用“模型输出完整 HTML”。
- 第一阶段校验只做兜底，不做自动重排版，不把直出 HTML 改造成 JSON 渲染流。
- 生成结果统一保存到 `backend/generated/ppt_html/<task_id>/index.html`，方便后续稳定预览。

---

## 三、实施任务

### 任务 1：先锁定独立 `ppt` 模块的 API 契约

**涉及文件：**
- 新建：`backend/tests/modules/test_ppt_task_contract.py`
- 修改：`backend/tests/modules/test_module_registration.py`
- 新建：`backend/app/modules/ppt/schemas.py`
- 新建：`backend/app/modules/ppt/router.py`
- 修改：`backend/app/core/container.py`

- [ ] **步骤 1：先写失败测试，定义 API 契约**

测试至少覆盖：
- `POST /api/v1/ppt/tasks` 能创建任务
- `GET /api/v1/ppt/tasks/{task_id}` 能查询任务
- `POST /api/v1/ppt/tasks/{task_id}/run` 能触发执行
- 返回结构统一走 `ApiResponse`
- 任务初始状态为 `pending`
- `artifact_kind` 固定为 `html`

- [ ] **步骤 2：运行测试，确认当前因路由缺失而失败**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_task_contract.py -v
```
期望：
- 因 `404` 或模块不存在而失败。

- [ ] **步骤 3：补齐 `schemas.py` 和 `router.py` 骨架**

建议定义：
- `PptTaskCreateRequest`
  - `topic: str`
  - `prompt: str`
  - `title: str | None = None`
- `PptTaskLogSchema`
  - `step: str`
  - `message: str`
- `PptTaskSchema`
  - `task_id`
  - `topic`
  - `prompt`
  - `title`
  - `status`
  - `current_step`
  - `artifact_kind = "html"`
  - `preview_url`
  - `artifact_path`
  - `error_message`
  - `logs`

路由最少包含：
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /tasks/{task_id}/run`

- [ ] **步骤 4：在 `container.ROUTER_REGISTRY` 中注册新模块**

新增：
- `("app.modules.ppt.router", "/api/v1/ppt")`

- [ ] **步骤 5：重新运行契约测试与模块注册测试**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_task_contract.py tests/modules/test_module_registration.py -v
```
期望：
- 新增的 `ppt` 路由全部通过。

- [ ] **步骤 6：提交**

```bash
git add backend/tests/modules/test_ppt_task_contract.py \
  backend/tests/modules/test_module_registration.py \
  backend/app/modules/ppt/schemas.py \
  backend/app/modules/ppt/router.py \
  backend/app/core/container.py
git commit -m "feat: add ppt task API contract"
```

### 任务 2：原样引入上游 `guizang-ppt-skill` 资产

**涉及文件：**
- 新建：`backend/app/modules/ppt/assets/guizang/SKILL.md`
- 新建：`backend/app/modules/ppt/assets/guizang/template.html`
- 新建：`backend/app/modules/ppt/assets/guizang/references/layouts.md`
- 新建：`backend/app/modules/ppt/assets/guizang/references/themes.md`
- 新建：`backend/app/modules/ppt/assets/guizang/references/components.md`
- 新建：`backend/app/modules/ppt/assets/guizang/references/checklist.md`
- 新建：`backend/tests/modules/test_ppt_prompt_assets.py`
- 新建：`backend/app/services/ppt_html_prompt_assets.py`

- [ ] **步骤 1：先写失败测试，定义资产加载器行为**

测试至少校验：
- 能加载 `skill_md`
- 能加载 `template_html`
- 能加载 `layouts_md`
- 能加载 `themes_md`
- 能加载 `components_md`
- 能加载 `checklist_md`
- `template_html` 中包含 `<main id="deck">`
- `skill_md` 中包含 `guizang-ppt-skill`

- [ ] **步骤 2：运行测试，确认当前因文件和加载器缺失而失败**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_prompt_assets.py -v
```
期望：
- import error 或文件缺失失败。

- [ ] **步骤 3：把上游文件原样拷贝到本仓库**

需要拷贝：
- `SKILL.md`
- `assets/template.html`
- `references/layouts.md`
- `references/themes.md`
- `references/components.md`
- `references/checklist.md`

注意：
- 保留来源说明
- 后续如果升级上游版本，优先比对 diff，不要手改本地版本

- [ ] **步骤 4：实现一个只负责读取这些文件的资产加载器**

建议：
- 类名：`PptHtmlPromptAssets`
- 方法：`load() -> dict[str, str]`
- 返回 key：
  - `skill_md`
  - `template_html`
  - `layouts_md`
  - `themes_md`
  - `components_md`
  - `checklist_md`

- [ ] **步骤 5：重新运行资产加载测试**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_prompt_assets.py -v
```
期望：
- 资产能被稳定加载。

- [ ] **步骤 6：提交**

```bash
git add backend/app/modules/ppt/assets/guizang \
  backend/tests/modules/test_ppt_prompt_assets.py \
  backend/app/services/ppt_html_prompt_assets.py
git commit -m "feat: vendor guizang ppt prompt assets"
```

### 任务 3：实现完整 HTML prompt 组装和轻量校验器

**涉及文件：**
- 新建：`backend/app/services/ppt_html_generate_service.py`
- 新建：`backend/app/services/ppt_html_validator.py`
- 新建：`backend/tests/modules/test_ppt_html_validator.py`

- [ ] **步骤 1：先写失败测试，定义 HTML 校验边界**

建议校验两类情况：
- 完整 deck HTML 能通过
- 缺少关键结构时直接拒绝

第一期校验最少检查：
- `<!DOCTYPE html>`
- `<html`
- `<title>`
- `id="deck"`
- `class="slide`

同时给出软校验：
- 出现 `[必填]` 记为错误
- 缺少 `data-anim` 记为 warning
- 缺少 hero slide 记为 warning

- [ ] **步骤 2：运行测试，确认当前因校验器缺失而失败**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_html_validator.py -v
```
期望：
- import error。

- [ ] **步骤 3：实现轻量 HTML 校验器**

目标：
- 只做第一阶段兜底
- 不自动修 HTML
- 不把直出 HTML 改造成模板渲染

建议暴露：
- `HtmlValidationReport`
- `validate_generated_html(html: str) -> HtmlValidationReport`

- [ ] **步骤 4：实现完整 HTML 生成服务**

建议类：`PptHtmlGenerateService`

职责：
- 加载 vendored 资产
- 组装 `system_prompt`
- 组装 `user_prompt`
- 调用现有 `LlmClient.complete(...)`
- 要求模型“只返回 HTML，不要 Markdown fence，不要解释”
- 对返回结果调用 `validate_generated_html`
- 返回 HTML 字符串

prompt 组装建议：
- `system_prompt` 里拼接：
  - 高层生成要求
  - `SKILL.md`
  - `layouts.md`
  - `themes.md`
  - `components.md`
  - `checklist.md`
- `user_prompt` 里拼接：
  - `topic`
  - 用户请求 `prompt`
  - “请基于模板输出一份完整、可运行的 HTML 文档”
  - 原始 `template.html`

- [ ] **步骤 5：重新运行校验测试**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_html_validator.py -v
```
期望：
- 校验逻辑通过。

- [ ] **步骤 6：提交**

```bash
git add backend/app/services/ppt_html_generate_service.py \
  backend/app/services/ppt_html_validator.py \
  backend/tests/modules/test_ppt_html_validator.py
git commit -m "feat: add ppt html prompt and validation services"
```

### 任务 4：补齐任务存储、执行编排和产物落盘

**涉及文件：**
- 新建：`backend/app/modules/ppt/repository.py`
- 新建：`backend/app/modules/ppt/service.py`
- 新建：`backend/app/modules/ppt/dependencies.py`
- 修改：`backend/app/config.py`
- 新建：`backend/tests/modules/test_ppt_generate_service.py`

- [ ] **步骤 1：先写失败测试，定义执行流程**

测试至少覆盖：
- 创建任务后能从 repository 取回
- 执行任务后状态变成 `succeeded`
- 成功后产物文件存在
- `preview_url` 正确
- `artifact_path` 指向真实文件

- [ ] **步骤 2：运行测试，确认当前因 repository / service 缺失而失败**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_generate_service.py -v
```
期望：
- import error 或类缺失。

- [ ] **步骤 3：在配置中新增生成目录配置**

建议新增：
- `GENERATED_ROOT`

目标路径统一为：
- `backend/generated/ppt_html/<task_id>/index.html`

- [ ] **步骤 4：实现 in-memory repository**

建议类：`PptRepository`

至少提供：
- `create_task(...)`
- `get_task(task_id)`
- `save_task(task)`

第一期可以继续沿用当前项目里 `canvas` 模块类似的单例内存存储风格。

- [ ] **步骤 5：实现 `PptService` 编排逻辑**

职责：
- `create_task(payload)`
- `get_task(task_id)`
- `run_task(task_id)`

`run_task` 里建议流程：
1. 读任务
2. 标记为 `running/generating`
3. 调 `PptHtmlGenerateService.generate_html(...)`
4. 创建 `backend/generated/ppt_html/<task_id>/`
5. 保存 `index.html`
6. 更新任务状态为 `succeeded`
7. 设置：
   - `artifact_path`
   - `preview_url = /api/v1/ppt/tasks/<task_id>/preview`
8. 记录日志

失败时：
- 置为 `failed`
- 写入 `error_message`
- 记录失败日志

- [ ] **步骤 6：实现依赖注入**

建议沿用现有模块模式：
- `PptRepository` 单例
- `PptService` 单例
- `get_ppt_service()` 作为 Depends 入口

- [ ] **步骤 7：重新运行执行编排测试**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_generate_service.py -v
```
期望：
- 任务执行后真实写出 `index.html`。

- [ ] **步骤 8：提交**

```bash
git add backend/app/config.py \
  backend/app/modules/ppt/repository.py \
  backend/app/modules/ppt/service.py \
  backend/app/modules/ppt/dependencies.py \
  backend/tests/modules/test_ppt_generate_service.py
git commit -m "feat: add ppt task orchestration and artifact persistence"
```

### 任务 5：增加预览接口，并补齐文档边界说明

**涉及文件：**
- 修改：`backend/app/modules/ppt/router.py`
- 修改：`API.md`
- 新建：`backend/app/modules/ppt/__init__.py`

- [ ] **步骤 1：先写失败测试，定义 HTML 预览行为**

测试至少校验：
- 任务执行后可访问 `/api/v1/ppt/tasks/{task_id}/preview`
- 返回 `200`
- `content-type` 为 `text/html`
- 响应内容包含 `<!DOCTYPE html>`

- [ ] **步骤 2：运行测试，确认当前因 preview 路由缺失而失败**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_task_contract.py::test_preview_endpoint_serves_generated_html -v
```
期望：
- `404`。

- [ ] **步骤 3：在 router 中新增 preview 路由**

建议：
- 从任务记录拿 `artifact_path`
- 用 `FileResponse` 返回
- `media_type` 设置为 `text/html; charset=utf-8`

- [ ] **步骤 4：更新 `API.md`，明确模块边界**

要写清楚：
- `PPT` 模块独立于 `board`
- 它负责生成单文件 HTML deck
- 不负责飞书白板节点渲染

建议补充接口文档：
- `POST /ppt/tasks`
- `POST /ppt/tasks/{task_id}/run`
- `GET /ppt/tasks/{task_id}`
- `GET /ppt/tasks/{task_id}/preview`

- [ ] **步骤 5：重新运行预览与 API 测试**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_task_contract.py tests/modules/test_module_registration.py -v
```
期望：
- 预览路由和文档相关测试通过。

- [ ] **步骤 6：提交**

```bash
git add backend/app/modules/ppt/router.py \
  backend/app/modules/ppt/__init__.py \
  API.md
git commit -m "feat: add ppt preview delivery"
```

### 任务 6：端到端验证与交接备注

**涉及文件：**
- 修改：`docs/superpowers/plans/2026-04-28-magazine-ppt-html-module.md`

- [ ] **步骤 1：跑完整 PPT 模块测试集**

运行：
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_ppt_task_contract.py tests/modules/test_ppt_prompt_assets.py tests/modules/test_ppt_html_validator.py tests/modules/test_ppt_generate_service.py -v
```
期望：
- 契约、资产加载、HTML 校验、任务执行、预览接口全部通过。

- [ ] **步骤 2：手工做一次 API smoke test**

建议跑一段最小脚本：
- 创建任务
- 执行任务
- 打印 `task_id`
- 打印 `preview_url`
- 打印 `artifact_path`

期望：
- 输出 `ppt-task-...`
- 输出 `/api/v1/ppt/tasks/.../preview`
- 输出落盘后的绝对路径，且以 `index.html` 结尾

- [ ] **步骤 3：给下一个执行者补充交接注意事项**

建议写进文档：
- 第一阶段故意保留“模型直出完整 HTML”，不要提前改造成 JSON 结构化渲染。
- 如果后面坏页概率变高，先加强校验，再决定是否切到模板驱动渲染。
- 上游 vendored 文件升级时先 diff，不要本地手改。
- 和 `canvas/board` 的公共能力若要抽取，放到 `app/services`，不要跨模块互相侵入。

- [ ] **步骤 4：提交**

```bash
git add docs/superpowers/plans/2026-04-28-magazine-ppt-html-module.md
git commit -m "docs: finalize magazine ppt module handoff plan"
```

---

## 四、覆盖检查

- 独立 `ppt` 模块边界：由任务 1、4、5 覆盖。
- 原样复用上游 skill 资产与 prompt 规则：由任务 2、3 覆盖。
- 模型直接输出完整 HTML：由任务 3 覆盖。
- 文件落盘与预览接口：由任务 4、5 覆盖。
- 可直接交接执行：由任务 6 覆盖。

## 五、执行提醒

- 这份方案是给“下一个任务”直接执行的，所以优先保证边界清晰和步骤顺序，不追求一次性做太多增强。
- 第一阶段最重要的是“先通路、先出同风格 HTML、先能预览”。
- 不要在第一阶段把问题复杂化成模板 AST、布局 DSL、或 HTML 二次编译器。
