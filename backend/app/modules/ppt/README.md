# PPT 模块

`backend.app.modules.ppt` 是 Eko 后端对 `backend/vendor/ppt_master` 的桥接层。

`backend/vendor/ppt_master` 是模板语义、执行流程、SVG 质量规则、后处理和 PPTX 导出的 source of truth。这里维护的是 Eko 侧的接入与适配，不再并行实现另一套本地 PPT 引擎。

## 主要入口

- `AipptGenerator`：桥接 Eko 输入与 vendored `ppt_master` 导出流程的主入口。
- `TemplateImportService` / `TemplatePack`：管理导入后的模板包与模板资源定位。
- `TemplateLibrary` / `validate_svg`：复用当前模块暴露的模板与 SVG 校验能力。
- `backend/vendor/ppt_master/scripts/`：实际后处理与导出脚本入口，桥接层默认按该目录约定执行。

## 快速使用

```python
import asyncio
from backend.app.modules.ppt import AipptGenerator

content = {
    "project_name": "demo",
    "pages": [
        {"layout": "cover", "title": "年度增长计划", "subtitle": "2026"},
        {"layout": "content", "title": "关键动作", "content": ["聚焦高意向用户", "优化转化链路"]},
        {"layout": "ending", "title": "谢谢", "subtitle": "Q&A"},
    ],
}

asyncio.run(AipptGenerator().generate(content, "demo.pptx"))
```

### 使用模板包

如果已经生成了模板包，可以直接指定 `template_dir`：

```python
asyncio.run(
    AipptGenerator(
        template_dir="backend/generated/template_packs/学术风/batch_01/variant_01_学术风_ref1_pack"
    ).generate(content, "demo.pptx")
)
```

## 约定

- SVG 原始输出目录：`svg_output/`
- SVG 后处理目录：`svg_final/`
- 演讲备注入口：`notes/total.md`
- 默认导出目录：`exports/`
- SVG 命名：`slide_01_cover.svg`、`slide_02_content.svg`
- 后处理脚本目录默认：`backend/vendor/ppt_master/scripts/`
- 必须按顺序执行：`total_md_split.py <project_path>`、`finalize_svg.py <project_path>`、`svg_to_pptx.py <project_path> -s final -o <output>`
- `IMAGE_BACKEND` 可选：`gemini`、`openai`、`qwen`、`zhipu`、`volcengine`
- `template_name` 可以直接指向 `backend/vendor/ppt_master/templates/layouts/<name>`
- `template_dir` 可以指向已导入生成的模板包目录
- `style_group` 是导入模板包时的一级风格目录，比如 `学术风`

如果当前仓库尚未放入 `ppt-master` 脚本，可以通过 `AipptGenerator(scripts_dir="...")` 指向外部脚本目录。
