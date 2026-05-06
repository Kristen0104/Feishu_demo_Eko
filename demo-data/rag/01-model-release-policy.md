# NovaMind 模型发布与分级策略

更新时间：2026-05-01
适用范围：NovaMind 内部基础模型、推理模型、多模态模型

## 1. 发布分级

- `research`：研究验证版本，只限小范围评估，不对客户暴露。
- `preview`：可用于设计伙伴试点，允许接入非核心业务。
- `stable`：默认生产版本，可用于正式商用。
- `legacy`：停止新增接入，仅保留存量迁移窗口。

## 2. 命名约定

- 通用文本模型：`nova-text-*`
- 推理增强模型：`nova-reason-*`
- 多模态模型：`nova-vision-*`
- 向量模型：`nova-embed-*`

示例：

- `nova-text-3.1-stable`
- `nova-reason-2.0-preview`
- `nova-vision-1.4-stable`

## 3. 默认接入策略

- 新客户默认推荐 `nova-text-3.1-stable`
- 对复杂规划、代码分析、长链路问答，优先推荐 `nova-reason-2.0-preview`
- 图片理解和图文问答使用 `nova-vision-1.4-stable`
- 知识库检索统一使用 `nova-embed-2-small`

## 4. 切换条件

满足以下任一条件，可以从 `preview` 升级到 `stable`：

1. 连续 14 天线上错误率低于 0.5%
2. 核心客户试点满意度不低于 4.3/5
3. 平均响应时延波动低于 10%

## 5. 已知限制

- `nova-reason-2.0-preview` 在超长上下文场景下成本偏高
- `nova-vision-1.4-stable` 对复杂表格结构的还原能力一般
- `nova-embed-2-small` 适合通用检索，不建议直接用于高精度重排序
