from __future__ import annotations

from app.config import Settings
from app.modules.aippt.llm_client import DeckPlan, DeckSlide, DeepSeekAIPPTClient
from app.modules.aippt.template_renderer import AIPPTTemplateRenderer, TextBoxSpec


def test_three_cards_template_renders_fixed_cards() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    plan = DeckPlan(
        title="校园AI项目答辩",
        subtitle="答辩演示",
        visual_style="clean_business",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        slides=[
            DeckSlide(
                slide_number=1,
                title="校园场景中的痛点",
                objective="先说明场景痛点和问题边界。",
                bullets=["信息碎片化", "流程繁琐", "缺统一入口"],
                template="three_cards",
                text_box=["信息碎片化，跨部门协作低效", "学生事务处理流程繁琐，响应慢", "AI应用场景分散，缺统一入口"],
                cards=["跨部门协作低效", "响应慢", "缺统一入口"],
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert 'viewBox="0 0 1280 720"' in svg
    assert "Key Cards" not in svg
    assert svg.count('<rect x="748"') == 3
    assert "跨部门协作低效" in svg


def test_timeline_template_renders_timeline_items() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    plan = DeckPlan(
        title="技术实现",
        subtitle="答辩演示",
        visual_style="clean_business",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        slides=[
            DeckSlide(
                slide_number=2,
                title="技术推进路径",
                objective="说明三阶段实施路径。",
                bullets=["阶段概述一", "阶段概述二", "阶段概述三"],
                template="timeline",
                text_box=["阶段概述一", "阶段概述二", "阶段概述三"],
                timeline_items=["阶段一：数据清洗与标注", "阶段二：模型训练与部署", "阶段三：飞书接入与闭环"],
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert "Timeline" in svg
    assert "阶段一" in svg
    assert "阶段二" in svg
    assert "阶段三" in svg


def test_metrics_template_renders_metric_items() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    plan = DeckPlan(
        title="项目成果",
        subtitle="答辩演示",
        visual_style="clean_business",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        slides=[
            DeckSlide(
                slide_number=3,
                title="量化成果",
                objective="展示三项核心指标。",
                bullets=["指标概述一", "指标概述二", "指标概述三"],
                template="metrics",
                text_box=["指标概述一", "指标概述二", "指标概述三"],
                metrics=["响应速度提升80%", "人工成本降低60%", "准确率达到99.5%"],
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert "Metrics" in svg
    assert "响应速度提升80%" in svg
    assert "人工成本降低60%" in svg
    assert "准确率达到99.5%" in svg


def test_generate_deck_plan_assigns_page_roles_and_content_templates() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    client._chat_completion = lambda *args, **kwargs: """
{
  "title": "测试标题",
  "subtitle": "测试副标题",
  "slides": [
    {"slide_number": 1, "title": "第一页", "objective": "目标1", "text_box": ["A"], "cards": ["B", "C", "D"], "visual_type": "cards"},
    {"slide_number": 2, "title": "第二页", "objective": "目标2", "text_box": ["A"], "comparison_items": ["现状A", "目标B", "差异C"], "visual_type": "comparison"},
    {"slide_number": 3, "title": "第三页", "objective": "目标3", "text_box": ["A"], "architecture_parent": "系统", "architecture_items": ["模块A", "模块B", "模块C"], "architecture_flow": ["输入", "处理", "输出"], "visual_type": "architecture"},
    {"slide_number": 4, "title": "第四页", "objective": "目标4", "text_box": ["A"], "process_items": ["步骤A", "步骤B", "步骤C"], "visual_type": "process"},
    {"slide_number": 5, "title": "第五页", "objective": "目标5", "text_box": ["A"], "cards": ["行动A", "行动B", "行动C"], "visual_type": "cards"}
  ]
}
""".strip()

    plan = client.generate_deck_plan("source", 5, "clean_business")

    assert [slide.template for slide in plan.slides] == ["cover", "comparison", "architecture", "process", "closing"]


def test_template_mode_does_not_auto_plan_generated_images_when_image_generation_is_enabled() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub", AIPPT_IMAGE_GENERATION_ENABLED=True))
    client._chat_completion = lambda *args, **kwargs: """
{
  "title": "测试标题",
  "subtitle": "测试副标题",
  "slides": [
    {"slide_number": 1, "title": "第一页", "objective": "目标1", "text_box": ["A"], "cards": ["B", "C", "D"], "visual_type": "cards"},
    {"slide_number": 2, "title": "第二页", "objective": "目标2", "text_box": ["A"], "process_items": ["步骤A", "步骤B", "步骤C"], "visual_type": "process"}
  ]
}
""".strip()

    plan = client.generate_deck_plan("source", 2, "ai_image_clean_business", design_mode="template")

    assert plan.execution_mode == "renderer"
    assert plan.image_resources == []


def test_free_design_mode_can_plan_pending_generated_images_when_image_generation_is_enabled() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub", AIPPT_IMAGE_GENERATION_ENABLED=True))
    client._chat_completion = lambda *args, **kwargs: """
{
  "title": "自由设计测试",
  "subtitle": "测试副标题",
  "visual_direction": "editorial product deck",
  "slides": [
    {"slide_number": 1, "title": "第一页", "objective": "目标1", "text_box": ["A"], "cards": ["B", "C", "D"], "visual_type": "cover", "layout_intent": "image-led cover", "page_rhythm": "anchor"},
    {"slide_number": 2, "title": "第二页", "objective": "目标2", "text_box": ["A"], "process_items": ["步骤A", "步骤B", "步骤C"], "visual_type": "process", "layout_intent": "open process", "page_rhythm": "dense"}
  ]
}
""".strip()

    plan = client.generate_deck_plan("source", 2, "ai_image_editorial", design_mode="free_design")

    assert plan.execution_mode == "free_design"
    assert plan.image_resources
    assert plan.image_resources[0]["status"] == "Pending"


def test_free_design_cover_injects_existing_image_when_executor_omits_it() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    client._chat_completion = lambda *args, **kwargs: """
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#F8FAFC"/>
  <text x="80" y="120" font-family="Arial" font-size="36" fill="#0F172A">封面</text>
</svg>
""".strip()
    plan = DeckPlan(
        title="自由设计",
        subtitle="测试",
        visual_style="editorial",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        execution_mode="free_design",
        image_resources=[
            {
                "filename": "cover_bg.png",
                "dimensions": "1920x1080",
                "purpose": "Cover background",
                "type": "Background",
                "status": "Generated",
            }
        ],
        slides=[
            DeckSlide(
                slide_number=1,
                title="封面",
                objective="测试图片注入",
                bullets=["A"],
                template="cover",
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert '<image href="../images/cover_bg.png"' in svg
    assert 'fill-opacity="0.74"' in svg


def test_free_design_sanitizes_clip_paths_before_ppt_master_quality_check() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    client._chat_completion = lambda *args, **kwargs: """
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs><clipPath id="c"><rect x="0" y="0" width="100" height="100"/></clipPath></defs>
  <rect width="1280" height="720" fill="#F8FAFC"/>
  <rect x="80" y="120" width="240" height="120" fill="#2563EB" clip-path="url(#c)"/>
  <text x="80" y="320" font-family="Arial" font-size="36" fill="#0F172A">内容</text>
</svg>
""".strip()
    plan = DeckPlan(
        title="自由设计",
        subtitle="测试",
        visual_style="editorial",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        execution_mode="free_design",
        slides=[
            DeckSlide(
                slide_number=1,
                title="封面",
                objective="测试剪裁清理",
                bullets=["A"],
                template="cover",
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert "clipPath" not in svg
    assert "clip-path" not in svg


def test_free_design_sanitizes_emoji_symbols_for_pptx_rendering() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    client._chat_completion = lambda *args, **kwargs: """
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#F8FAFC"/>
  <text x="80" y="120" font-family="Arial" font-size="36" fill="#0F172A">🎯 目标 ✅</text>
</svg>
""".strip()
    plan = DeckPlan(
        title="自由设计",
        subtitle="测试",
        visual_style="editorial",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        execution_mode="free_design",
        slides=[
            DeckSlide(
                slide_number=1,
                title="封面",
                objective="测试 emoji 清理",
                bullets=["A"],
                template="cover",
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert "🎯" not in svg
    assert "✅" not in svg
    assert "目标" in svg


def test_free_design_fallback_still_injects_existing_image() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    client._chat_completion = lambda *args, **kwargs: "<not-svg>"
    plan = DeckPlan(
        title="自由设计",
        subtitle="测试",
        visual_style="editorial",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        execution_mode="free_design",
        image_resources=[
            {
                "filename": "cover_bg.png",
                "dimensions": "1920x1080",
                "purpose": "Cover background",
                "type": "Background",
                "status": "Generated",
            }
        ],
        slides=[
            DeckSlide(
                slide_number=1,
                title="封面",
                objective="测试 fallback 图片注入",
                bullets=["A"],
                template="cover",
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert '<image href="../images/cover_bg.png"' in svg


def test_three_cards_truncates_overflow_text_without_ellipsis() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    long_card = "超长内容字段用于测试真实框约束是否生效" * 12
    plan = DeckPlan(
        title="测试",
        subtitle="测试",
        visual_style="clean_business",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        slides=[
            DeckSlide(
                slide_number=1,
                title="测试页",
                objective="测试目标",
                bullets=["A", "B", "C"],
                template="three_cards",
                cards=[long_card, long_card, long_card],
            )
        ],
    )

    svg = client.generate_slide_svg(plan, plan.slides[0], "# Design Spec")

    assert "…" not in svg
    assert long_card not in svg


def test_timeline_and_metrics_truncate_overflow_text_without_ellipsis() -> None:
    client = DeepSeekAIPPTClient(Settings(AIPPT_API_KEY="stub"))
    long_value = "This is a very long synthetic label for checking bounding box clipping behavior " * 6
    timeline_plan = DeckPlan(
        title="测试",
        subtitle="测试",
        visual_style="clean_business",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        slides=[
            DeckSlide(
                slide_number=2,
                title="时间线测试",
                objective="测试目标",
                bullets=["A", "B", "C"],
                template="timeline",
                timeline_items=[long_value, long_value, long_value],
            )
        ],
    )
    metrics_plan = DeckPlan(
        title="测试",
        subtitle="测试",
        visual_style="clean_business",
        palette=["#2563EB", "#DBEAFE", "#EFF6FF"],
        slides=[
            DeckSlide(
                slide_number=3,
                title="指标测试",
                objective="测试目标",
                bullets=["A", "B", "C"],
                template="metrics",
                metrics=[long_value, long_value, long_value],
            )
        ],
    )

    timeline_svg = client.generate_slide_svg(timeline_plan, timeline_plan.slides[0], "# Design Spec")
    metrics_svg = client.generate_slide_svg(metrics_plan, metrics_plan.slides[0], "# Design Spec")

    assert "…" not in timeline_svg
    assert "…" not in metrics_svg
    assert long_value not in timeline_svg
    assert long_value not in metrics_svg


def test_fit_text_to_box_shrinks_font_and_still_truncates_when_necessary() -> None:
    renderer = AIPPTTemplateRenderer()
    spec = renderer._RIGHT_PANEL_BOX_SPECS["timeline"][0]

    fitted = renderer._fit_text_to_box(
        "阶段一：完成多源数据清洗、标注规范统一与训练样本构建，确保底层数据质量稳定并满足上线要求。",
        spec=spec,
    )

    assert fitted.font_size <= spec.font_size
    assert len(fitted.lines) <= 2
    assert all("…" not in line for line in fitted.lines)
    assert renderer._lines_fit_box(
        fitted.lines,
        box_width=spec.box_width,
        box_height=spec.box_height,
        font_size=fitted.font_size,
        line_height=fitted.line_height,
    )


def test_dense_left_points_stay_inside_content_panel() -> None:
    renderer = AIPPTTemplateRenderer()
    profile = renderer._body_density_profile("dense")
    svg = renderer.render(
        deck_title="测试 PPT",
        slide_number=1,
        template_name="three_cards",
        page_title="语义扩写测试",
        objective="验证 dense 模式不会把左侧正文挤出面板。",
        text_box=[
            "第一条正文需要足够完整，说明背景、判断依据和业务影响。",
            "第二条正文需要展开关键场景，避免只保留一个短标签。",
            "第三条正文需要说明行动抓手，帮助读者理解下一步。",
            "第四条正文需要承接前后页面，让叙事保持连贯。",
            "第五条正文需要给出结论或验证口径，保证信息完整。",
            "第六条正文作为计划内容存在，但视觉渲染应控制在安全范围内。",
        ],
        right_items=["背景", "行动", "验证"],
        accent="#C53030",
        accent_soft="#FED7D7",
        accent_pale="#FFF5F5",
        body_density="dense",
    )

    assert profile["left_points"] == 5
    assert svg.count('<circle cx="108"') == 5
    assert "第六条正文" not in svg
    assert "Key Cards" not in svg
