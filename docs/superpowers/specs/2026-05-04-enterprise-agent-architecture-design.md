# 企业级 Agent 架构设计

## 目标

把 Eko 的 Agent 层从“关键词判断 + 局部补丁”的写法，升级成清晰、可追踪、可测试、可扩展的企业级编排系统。

新的链路必须满足几个基本要求：

1. 用户每说一句话，都把用户输入、会话上下文、历史消息、当前产物、可用工具、相关知识一起交给大模型判断。
2. 大模型负责意图理解、任务规划、工具选择和下一步决策。
3. 代码里的规则只做边界保护、权限校验、参数校验和兜底，不再充当主要决策大脑。
4. 每一步内部动作都要产生可展示的轨迹事件，前端能看到“为什么这么做、现在做到哪一步”。
5. PPT、文档、任务、搜索、RAG 等能力都通过统一工具注册表暴露给 Agent。
6. 遇到信息不足时，Agent 明确进入“等待澄清”状态，而不是靠零散字符串猜测。

## 核心判断

这个项目的问题不是某一个按钮、某一个 PPT 分支、某一个关键词没覆盖，而是 Agent 根链路不成立。

正确链路应该是：

```text
用户输入
  -> 装载会话上下文
  -> 检索相关知识和历史材料
  -> 大模型理解意图并规划
  -> 大模型选择工具
  -> 执行工具
  -> 读取工具结果
  -> 决定继续调用、追问用户或完成回复
  -> 前端展示规划、进度、产物和最终结果
```

因此后续改造重点不是继续写关键词分支，而是把 Agent 做成标准的“状态图 + 工具调用 + 可观测轨迹”。

## 技术选型

推荐使用 `LangChain Core + LangGraph`。

`LangChain Core` 负责：

1. 模型调用封装。
2. 工具参数结构定义。
3. 结构化输出。
4. 提示词和消息结构。
5. RAG 里的文档加载、文本切分、检索器、向量库抽象。

`LangGraph` 负责：

1. 把 Agent 做成明确的状态图。
2. 控制规划、工具调用、工具结果、澄清、最终回复等节点流转。
3. 管理可恢复状态。
4. 支持多步工具调用。
5. 让每个节点天然适合输出轨迹事件。

关于 RAG：LangGraph 本身不是“知识库框架”，它更像编排层。RAG 的快速实现主要来自 LangChain 的检索器、文档加载器、文本切分器、向量表示和向量库。LangGraph 应该把“检索”作为一个节点或工具纳入 Agent 流程。

## 总体架构

```text
前端
  |
  | 用户输入 / 视觉状态 / 操作请求
  v
AgentTurnController
  |
  | 读取会话、消息、产物、权限、同步状态
  v
AgentRuntime
  |
  | 构造 AgentState
  v
LangGraph 工作流
  |
  +--> 上下文节点
  |      装载历史、当前产物、飞书上下文、任务状态
  |
  +--> 检索节点
  |      用 RAG 检索相关文档、历史会话、项目知识
  |
  +--> 规划节点
  |      大模型判断意图、规划步骤、选择下一步
  |
  +--> 工具节点
  |      执行 PPT、文档、任务、搜索、知识库等工具
  |
  +--> 结果观察节点
  |      归纳工具结果，决定继续、追问或结束
  |
  +--> 澄清节点
  |      信息不足时生成问题并保存待确认状态
  |
  +--> 结束节点
         输出最终回复、产物、任务状态和轨迹
```

## 后端模块边界

建议拆成这些模块：

```text
backend/app/modules/agent/
  controller.py
  runtime.py
  state.py
  graph.py
  prompts.py
  events.py
  memory.py
  rag.py
  tools/
    registry.py
    ppt.py
    document.py
    task.py
    search.py
    knowledge.py
  guards/
    policy.py
    validation.py
    permissions.py
```

模块职责：

1. `controller.py`：处理 API 入参、会话读取、事务边界、返回结构。
2. `runtime.py`：统一运行一次 Agent turn。
3. `state.py`：定义 AgentState、ArtifactState、ClarificationState。
4. `graph.py`：定义 LangGraph 节点和边。
5. `prompts.py`：维护系统提示词、规划提示词、工具选择提示词。
6. `events.py`：把内部步骤转换成前端可展示的轨迹事件。
7. `memory.py`：维护会话记忆、长期偏好、最近上下文。
8. `rag.py`：封装检索、切分、索引、引用来源。
9. `tools/`：所有业务能力都用标准 Tool 接口暴露。
10. `guards/`：做权限、参数、安全和业务边界校验。

## AgentState

`AgentState` 是整个图的唯一状态入口，不能让节点互相偷传零散变量。

建议字段：

```python
class AgentState(TypedDict):
    session_id: str
    user_id: str
    user_message: str
    locale: str
    messages: list
    recent_history: list
    current_artifact: dict | None
    available_artifacts: list
    feishu_context: dict
    retrieved_context: list
    pending_clarification: dict | None
    plan: dict | None
    selected_tool: str | None
    tool_args: dict | None
    tool_results: list
    trace_events: list
    final_response: dict | None
    errors: list
```

关键原则：

1. 所有节点只读写 `AgentState`。
2. 每次节点完成都追加轨迹事件。
3. 待澄清状态必须结构化保存，下一轮用户回复时继续同一个任务。
4. 产物相关状态要明确区分“新建”和“修改当前产物”。

## Prompt 输入

每次调用大模型时，至少包含：

1. 系统级角色和边界。
2. 当前用户原始输入。
3. 最近对话历史。
4. 当前会话业务上下文。
5. 当前产物摘要。
6. 已检索到的 RAG 上下文。
7. 可用工具列表和参数结构。
8. 已存在待澄清状态时的恢复信息。
9. 输出格式要求。

大模型必须输出结构化决策，例如：

```json
{
  "intent": "create_presentation",
  "confidence": 0.92,
  "requires_clarification": true,
  "clarification_question": "你希望用模板模式还是自由设计？",
  "plan": [
    "理解 PPT 主题和目标",
    "确认生成模式",
    "创建 PPT 任务",
    "同步任务状态"
  ],
  "next_action": "ask_clarification",
  "tool_name": null,
  "tool_args": null
}
```

## 工具注册表

所有工具必须通过统一注册表暴露给 Agent，不允许散落在业务服务里临时写分支调用。

初始工具建议：

1. `ppt_create`：创建新 PPT。
2. `ppt_edit`：修改当前 PPT 的指定细节。
3. `ppt_regenerate`：基于主题重新生成 PPT。
4. `document_create`：生成文档。
5. `task_create`：创建任务。
6. `task_update`：同步任务状态。
7. `conversation_search`：搜索会话历史。
8. `knowledge_search`：RAG 知识库检索。
9. `artifact_lookup`：读取当前或历史产物。

工具实现要求：

1. 每个工具有明确输入参数结构。
2. 每个工具返回结构化观察结果。
3. 工具本身不负责猜意图。
4. 工具失败时返回可恢复错误，不直接吞掉异常。
5. 工具调用前统一经过权限和参数保护规则。

## RAG 设计

RAG 不是单独页面功能，而是 Agent 的上下文能力。它应该服务于规划、问答、文档生成、PPT 生成和任务处理。

第一阶段实现范围：

1. 索引项目内知识文档。
2. 索引会话摘要。
3. 索引已生成产物的标题、摘要、结构和关键字段。
4. 使用向量表示和向量库做相似检索。
5. 返回来源、片段、相关度和可展示引用。

建议模块：

```text
backend/app/modules/agent/rag.py
backend/app/modules/agent/tools/knowledge.py
backend/app/modules/knowledge/
  ingest.py
  splitter.py
  embeddings.py
  vector_store.py
  retriever.py
```

推荐存储：

1. 开发阶段可以先用本地向量库或 SQLite 向量扩展。
2. 企业化版本建议使用 PostgreSQL + pgvector。
3. 文档原文、切片、向量表示、元数据分开存。

RAG 数据结构：

```python
class RetrievedChunk(TypedDict):
    source_id: str
    source_type: str
    title: str
    content: str
    score: float
    metadata: dict
```

在 LangGraph 中，RAG 可以有两种方式：

1. 固定节点：每轮先检索一次，把结果写入 `retrieved_context`。
2. 工具调用：由大模型决定是否调用 `knowledge_search`。

建议先做固定节点 + 工具调用的组合：

1. 固定节点提供基础上下文，避免模型裸猜。
2. 工具调用允许模型在复杂任务中追加检索。

## 规划展示

前端应该展示真实轨迹，而不是模拟进度。

这里要做成类似 Claude Code 的规划体验：Agent 在真正执行工具前，先把自己的任务理解、执行计划、需要确认的问题输出给用户；执行过程中持续更新计划状态；完成后输出实际结果、调用过的工具和剩余风险。

规划不是装饰 UI，而是 Agent 主链路的一部分。没有规划，就不应该直接调用 PPT、文档、任务等业务工具，除非用户请求非常简单且可以一步完成。

规划输出至少包含：

1. `goal`：Agent 理解到的用户目标。
2. `intent`：结构化意图。
3. `assumptions`：当前做出的关键假设。
4. `missing_info`：缺失信息。
5. `steps`：准备执行的步骤列表。
6. `next_action`：下一步是调用工具、追问用户，还是直接回复。
7. `tool_candidates`：可能会用到的工具。
8. `visible_summary`：给用户看的中文摘要。

计划步骤需要有状态：

```text
pending：待处理
in_progress：处理中
completed：已完成
blocked：等待用户或外部系统
failed：失败
```

前端展示时，用户应该能看到类似这样的内容：

```text
我理解你要生成一份动漫发展 PPT。

计划：
1. 梳理主题和目标受众
2. 判断是否需要模板模式或自由设计
3. 等你确认模式
4. 创建 PPT 任务
5. 同步任务状态并展示预览

当前需要确认：你希望用模板模式，还是自由设计？
```

用户回复“模板”后，计划应继续更新：

```text
已确认：模板模式。

继续执行：
1. 恢复刚才的 PPT 任务
2. 调用 PPT 创建工具
3. 写入生成结果
4. 同步任务状态
5. 展示 PPT 预览
```

事件类型建议：

```text
turn_started
context_loaded
retrieval_started
retrieval_completed
plan_created
clarification_requested
tool_selected
tool_started
tool_completed
artifact_created
artifact_updated
final_response_created
turn_completed
turn_failed
```

PPT 场景示例：

```text
1. 读取用户需求
2. 检索相关上下文
3. 判断为 PPT 生成任务
4. 发现未指定生成模式
5. 追问模板模式或自由设计
```

用户回复“模板”后：

```text
1. 恢复待确认的 PPT 任务
2. 将生成模式设为模板模式
3. 调用 ppt_create
4. 同步任务状态
5. 展示生成结果
```

## 澄清机制

澄清不是普通聊天，而是 Agent 状态。

结构：

```python
class ClarificationState(TypedDict):
    clarification_id: str
    original_user_message: str
    intent: str
    missing_fields: list[str]
    question: str
    candidate_values: dict
    expires_at: str | None
```

规则：

1. 用户下一条短回复优先尝试匹配待澄清状态。
2. 匹配成功后恢复原始任务，而不是把“模板”当成普通模板咨询。
3. 匹配失败时再进入普通意图识别。
4. 澄清状态完成后必须清理。

## PPT 场景要求

PPT 是当前最关键的业务验证链路。

必须支持：

1. 用户要求生成 PPT，但未指定模式时，展示规划并追问“模板模式 / 自由设计”。
2. 用户选择模板模式后，创建稳定可控的 PPT。
3. 用户选择自由设计后，允许更强视觉表达。
4. 用户说“修改某一页某个细节”时，识别为编辑当前 PPT，不重新生成。
5. 用户说“重新生成一个”时，识别为新任务，并重新确认必要参数。
6. 前端展示的 PPT 预览必须来自真实产物，不允许只靠意图字段伪造预览。

## 保护规则

规则层只做保护，不替代大模型决策。

需要的保护规则：

1. 权限校验。
2. 工具参数校验。
3. 产物是否存在校验。
4. 幂等保护。
5. 用户确认要求。
6. 文件大小、格式、页面数量限制。
7. 敏感操作拦截。

示例：

```text
大模型决定：调用 ppt_edit
保护规则判断：当前没有 PPT 产物
结果：转入澄清，询问用户要修改哪一个 PPT
```

## 前后端联调要求

后端返回：

1. `messages`：用户可见回复。
2. `trace_events`：真实执行轨迹。
3. `plan`：结构化规划。
4. `task_status`：任务状态。
5. `artifacts`：真实产物。
6. `pending_clarification`：待用户补充的信息。

前端要求：

1. 对话区展示用户可见回复。
2. 中间区展示轨迹和产物。
3. 右侧展示上下文来源、关联文件、同步状态和活动记录。
4. loading、失败、空状态都要真实。
5. 不能用静态假数据冒充真实 Agent 执行。

## 迁移计划

### 阶段一：整理边界

1. 新建 Agent 模块骨架。
2. 定义 AgentState。
3. 定义轨迹事件结构。
4. 把现有 PPT、文档、任务能力包成工具。
5. 前端改为消费真实轨迹。

完成标准：

1. 不再靠意图字段生成假产物。
2. PPT 生成和编辑都通过工具执行。
3. 用户能看到真实规划步骤。

### 阶段二：接入 LangGraph

1. 安装并封装 LangChain Core 和 LangGraph。
2. 实现上下文、检索、规划、工具、结果观察、结束节点。
3. 把现有 AgentService 改成调用 AgentRuntime。
4. 保留旧接口返回格式，降低前端迁移成本。

完成标准：

1. 每轮用户输入都走图。
2. 工具选择由大模型结构化输出决定。
3. 轨迹能完整反映图节点。

### 阶段三：接入 RAG

1. 建立知识入库流程。
2. 索引会话摘要和产物摘要。
3. 实现 `knowledge_search` 工具。
4. 在 LangGraph 中加入检索节点。
5. 前端展示检索来源。

完成标准：

1. Agent 能引用项目知识和历史会话。
2. 生成 PPT 或文档时能使用检索上下文。
3. 用户能看到“上下文来源”不是空壳。

### 阶段四：企业化完善

1. 补齐权限、审计、重试、超时和错误恢复。
2. 完成可观测日志。
3. 建立端到端测试脚本。
4. 做真实浏览器视觉验证。
5. 整理 API 文档和运维配置。

完成标准：

1. 核心链路稳定。
2. 错误可定位。
3. 前后端状态一致。
4. 新工具接入不需要改主流程。

## 测试策略

优先做集成测试和端到端测试。

必要测试：

1. 用户请求生成 PPT，Agent 追问模式。
2. 用户回复“模板”，Agent 恢复原任务并生成 PPT。
3. 用户要求修改当前 PPT 某个细节，Agent 调用编辑工具。
4. 用户重新生成 PPT，Agent 创建新任务。
5. RAG 返回上下文后，Agent 在规划中使用检索结果。
6. 工具失败时，前端展示失败状态和恢复建议。
7. 浏览器视觉验证：规划、对话、产物、右侧上下文都能正常显示。

## 非目标

短期内不做这些事：

1. 一次性重写所有业务模块。
2. 让 LangGraph 直接侵入所有业务服务。
3. 把规则系统继续扩大成另一个“假 Agent”。
4. 为了演示效果继续塞假数据。

## 最终完成标准

这个架构改造完成后，项目应该具备这些特征：

1. 用户输入由大模型理解，而不是关键词分支主导。
2. 工具调用有统一 registry。
3. 每个 Agent turn 都有清楚的状态、规划、工具调用和结果。
4. 前端展示的是后端真实轨迹。
5. RAG 能给 Agent 提供项目知识和历史上下文。
6. PPT 生成、编辑、重新生成能在真实浏览器里跑通。
7. 新增业务工具时，只需要注册工具和补测试，不需要重写主链路。
