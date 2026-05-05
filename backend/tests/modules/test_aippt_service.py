from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from app.config import Settings
from app.modules.aippt.file_parser import FileParser
from app.modules.aippt.job_store import JobStore
from app.modules.aippt.llm_client import DeckPlan, DeckSlide
from app.modules.aippt.ppt_master_runner import PPTMasterRunner
from app.modules.aippt.schemas import PPTGenerationRequest
from app.modules.aippt.service import AIPPTService


class FakeLLMClient:
    def generate_deck_plan(self, source_text: str, page_count: int, style: str) -> DeckPlan:
        _ = (source_text, style)
        return DeckPlan(
            title="AI PPT",
            subtitle="Generated subtitle",
            visual_style="clean blue dashboard",
            palette=["#2563EB", "#0F172A", "#E2E8F0"],
            slides=[
                DeckSlide(
                    slide_number=index,
                    title=f"Slide {index}",
                    objective=f"Objective {index}",
                    bullets=[f"Bullet {index}.1", f"Bullet {index}.2"],
                    visual="cards",
                )
                for index in range(1, page_count + 1)
            ],
        )

    def generate_design_spec(self, source_text: str, page_count: int, style: str, plan: DeckPlan) -> str:
        _ = (source_text, page_count, style, plan)
        return "# Design Spec\n\n## Topic\nTest"

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        _ = (plan, design_spec)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#ffffff"/>
  <text x="80" y="120" font-family="Arial" font-size="36">{slide.title}</text>
</svg>"""

    def generate_speaker_notes(self, design_spec: str, source_text: str, plan: DeckPlan) -> str:
        _ = (design_spec, source_text)
        return "\n\n".join(
            f"# slide_{slide.slide_number:02d}\n\nNotes for {slide.title}"
            for slide in plan.slides
        )


class OutlineRecordingLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.deck_plan_source_text = ""

    def generate_content_outline(self, source_text: str, page_count: int, style: str, *, design_mode: str = "template") -> str:
        self.calls.append(f"outline:{design_mode}:{page_count}:{style}:{source_text}")
        return "\n".join(
            [
                "# 详细版内容大纲",
                "",
                "## 第 1 页：业务背景与判断",
                "- 说明市场变化、用户需求和当前决策背景，避免只写标题。",
                "- 给出可直接放入 PPT 的完整业务句子。",
                "",
                "## 第 2 页：方案路径与执行抓手",
                "- 说明流程、角色、指标和落地节奏。",
            ]
        )

    def generate_deck_plan(self, source_text: str, page_count: int, style: str, *, design_mode: str = "template") -> DeckPlan:
        self.calls.append(f"plan:{design_mode}:{page_count}:{style}")
        self.deck_plan_source_text = source_text
        return DeckPlan(
            title="详细大纲驱动 PPT",
            subtitle="Generated subtitle",
            visual_style="clean blue dashboard",
            palette=["#2563EB", "#0F172A", "#E2E8F0"],
            body_density="detailed",
            slides=[
                DeckSlide(
                    slide_number=index,
                    title=f"Slide {index}",
                    objective=f"Objective {index}",
                    bullets=[
                        "说明市场变化、用户需求和当前决策背景，避免只写标题。",
                        "给出可直接放入 PPT 的完整业务句子。",
                        "说明流程、角色、指标和落地节奏。",
                        "明确下一步执行动作和验收口径。",
                    ],
                    text_box=[
                        "说明市场变化、用户需求和当前决策背景，避免只写标题。",
                        "给出可直接放入 PPT 的完整业务句子。",
                        "说明流程、角色、指标和落地节奏。",
                        "明确下一步执行动作和验收口径。",
                    ],
                    visual="cards",
                )
                for index in range(1, page_count + 1)
            ],
        )


class RecordingSlideLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.generated_slides: list[int] = []

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        self.generated_slides.append(slide.slide_number)
        return super().generate_slide_svg(plan, slide, design_spec)


class ThemeAwareRecordingLLMClient(RecordingSlideLLMClient):
    def generate_deck_plan(self, source_text: str, page_count: int, style: str) -> DeckPlan:
        _ = (source_text, style)
        theme_colors = {
            "bg": "#F0F4FF",
            "panel": "#FFFFFF",
            "primary": "#7C3AED",
            "accent": "#EDE9FE",
            "secondary_accent": "#F5F3FF",
            "text": "#1E1B4B",
            "text_secondary": "#4C4A6E",
            "border": "#C7D2FE",
        }
        return DeckPlan(
            title="紫色主题 PPT",
            subtitle="Generated subtitle",
            visual_style="clean purple dashboard",
            palette=["#7C3AED", "#EDE9FE", "#F5F3FF"],
            theme_colors=theme_colors,
            slides=[
                DeckSlide(
                    slide_number=index,
                    title=f"Slide {index}",
                    objective=f"Objective {index}",
                    bullets=[f"Bullet {index}.1", f"Bullet {index}.2"],
                    visual="cards",
                )
                for index in range(1, page_count + 1)
            ],
        )

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        self.generated_slides.append(slide.slide_number)
        primary = (plan.palette or ["#2563EB"])[0]
        bg = (getattr(plan, "theme_colors", None) or {}).get("bg", "#F8FAFC")
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="{bg}"/>
  <rect x="60" y="80" width="16" height="560" fill="{primary}"/>
  <text x="110" y="140" font-family="Arial" font-size="36">{slide.title}</text>
</svg>"""


class RetryThenValidLLMClient(FakeLLMClient):
    def __init__(self) -> None:
        self.slide_attempts = 0

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        self.slide_attempts += 1
        if self.slide_attempts == 1:
            return """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <foreignObject x="0" y="0" width="100" height="100"><div>bad</div></foreignObject>
</svg>"""
        return super().generate_slide_svg(plan, slide, design_spec)


class PendingImageLLMClient(FakeLLMClient):
    def generate_deck_plan(self, source_text: str, page_count: int, style: str) -> DeckPlan:
        plan = super().generate_deck_plan(source_text, page_count, style)
        plan.image_resources = [
            {
                "filename": "cover_bg.png",
                "dimensions": "1920x1080",
                "purpose": "Cover background",
                "type": "Background",
                "status": "Pending",
                "generation_description": "Should not be generated in template mode.",
            }
        ]
        return plan


class ParallelFreeDesignLLMClient(FakeLLMClient):
    def __init__(self, image_done: threading.Event, allow_image_finish: threading.Event) -> None:
        self.image_done = image_done
        self.allow_image_finish = allow_image_finish
        self.slide_events: list[tuple[int, bool]] = []

    def generate_deck_plan(self, source_text: str, page_count: int, style: str, *, design_mode: str = "template") -> DeckPlan:
        _ = (source_text, style, design_mode)
        return DeckPlan(
            title="Parallel Free Design",
            subtitle="Generated subtitle",
            visual_style="editorial",
            palette=["#2563EB", "#0F172A", "#E2E8F0"],
            execution_mode="free_design",
            image_resources=[
                {
                    "filename": "cover_bg.png",
                    "dimensions": "1920x1080",
                    "purpose": "Cover background",
                    "type": "Background",
                    "status": "Pending",
                    "generation_description": "Background image.",
                }
            ],
            slides=[
                DeckSlide(slide_number=index, title=f"Slide {index}", objective=f"Objective {index}", bullets=["A", "B"])
                for index in range(1, page_count + 1)
            ],
        )

    def generate_slide_svg(self, plan: DeckPlan, slide: DeckSlide, design_spec: str) -> str:
        self.slide_events.append((slide.slide_number, self.image_done.is_set()))
        if slide.slide_number == 2:
            self.allow_image_finish.set()
        return super().generate_slide_svg(plan, slide, design_spec)


class RecordingImageGenerator:
    def __init__(self) -> None:
        self.called = False

    def enabled(self) -> bool:
        return True

    def generate_pending_images(self, resources, project_dir: Path, prompt_builder):
        _ = (resources, project_dir, prompt_builder)
        self.called = True
        raise AssertionError("template mode must not invoke image generation")


class BlockingImageGenerator:
    def __init__(self, image_started: threading.Event, image_done: threading.Event, allow_finish: threading.Event) -> None:
        self.image_started = image_started
        self.image_done = image_done
        self.allow_finish = allow_finish

    def enabled(self) -> bool:
        return True

    def generate_pending_images(self, resources, project_dir: Path, prompt_builder):
        _ = (project_dir, prompt_builder)
        self.image_started.set()
        assert self.allow_finish.wait(timeout=2)
        updated = []
        for item in resources:
            copied = dict(item)
            copied["status"] = "Generated"
            copied["filename"] = copied.get("filename", "cover_bg.png")
            updated.append(copied)
        self.image_done.set()
        return updated


class FakeRunner(PPTMasterRunner):
    def __init__(self, vendor_root: Path) -> None:
        super().__init__(vendor_root)

    def validate_svg_output(self, project_dir: Path) -> None:
        (project_dir / "svg_quality_report.json").write_text("{}", encoding="utf-8")

    def export(self, project_dir: Path) -> Path:
        exports_dir = project_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        path = exports_dir / "deck_20260429_000000.pptx"
        path.write_bytes(b"fake-pptx")
        return path


def _build_service(
    tmp_path: Path,
    *,
    llm_client: FakeLLMClient | RetryThenValidLLMClient | None = None,
    image_generator=None,
) -> tuple[AIPPTService, Settings]:
    settings = Settings(
        AIPPT_STORAGE_DIR=str(tmp_path / "storage"),
        AIPPT_VENDOR_DIR=str(tmp_path / "vendor" / "ppt-master"),
        AIPPT_REDIS_QUEUE_ENABLED=False,
        AIPPT_SLIDE_CONCURRENCY=2,
    )
    service = AIPPTService(
        settings=settings,
        llm_client=llm_client or FakeLLMClient(),
        runner=FakeRunner(settings.AIPPT_VENDOR_PATH),
        parser=FileParser(settings.AIPPT_VENDOR_PATH),
        job_store=JobStore(
            jobs_root=settings.AIPPT_STORAGE_PATH / "jobs",
            uploads_root=settings.AIPPT_UPLOADS_PATH,
            projects_root=settings.AIPPT_PROJECTS_PATH,
            exports_root=settings.AIPPT_EXPORTS_PATH,
        ),
        image_generator=image_generator,
    )
    return service, settings


def test_aippt_service_creates_project_files_updates_status_and_export(tmp_path) -> None:
    service, settings = _build_service(tmp_path)

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=3, style="clean_business")
    )
    service.run_job(job.job_id)
    result = service.get_job(job.job_id)
    download_path = service.get_download_path(job.job_id)

    project_dir = settings.AIPPT_PROJECTS_PATH / job.job_id
    assert result.status == "done"
    assert result.download_url == f"/api/v1/ppt/files/{job.job_id}"
    assert result.progress == 100
    assert download_path.exists()
    assert (project_dir / "design_spec.md").exists()
    assert (project_dir / "spec_lock.md").exists()
    assert (project_dir / "svg_final").exists()
    assert (project_dir / "images").exists()
    assert (project_dir / "templates").exists()
    assert (project_dir / "exports").exists()
    assert (project_dir / "README.md").exists()
    spec_lock = (project_dir / "spec_lock.md").read_text(encoding="utf-8")
    assert "## canvas" in spec_lock
    assert "- viewBox: 0 0 1280 720" in spec_lock
    assert "## page_rhythm" in spec_lock
    assert "- P01:" in spec_lock
    assert (project_dir / "notes" / "total.md").exists()
    assert (project_dir / "metadata.json").exists()
    assert len(list((project_dir / "svg_output").glob("*.svg"))) == 3


def test_aippt_service_generates_detailed_outline_before_deck_plan(tmp_path) -> None:
    llm_client = OutlineRecordingLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="客户成功体系升级", page_count=2, style="clean_business")
    )
    service.run_job(job.job_id)

    project_dir = settings.AIPPT_PROJECTS_PATH / job.job_id
    outline_path = project_dir / "sources" / "content_outline.md"
    report = json.loads((project_dir / "generation_report.json").read_text(encoding="utf-8"))
    assert llm_client.calls[0].startswith("outline:template:2:clean_business")
    assert llm_client.calls[1] == "plan:template:2:clean_business"
    assert outline_path.exists()
    assert "详细版内容大纲" in outline_path.read_text(encoding="utf-8")
    assert "## 详细版内容大纲" in llm_client.deck_plan_source_text
    assert "客户成功体系升级" in llm_client.deck_plan_source_text
    assert report["content_outline"]["path"] == str(outline_path)
    assert report["deck"]["body_density"] == "detailed"


def test_aippt_current_ppt_edit_reuses_unmodified_slides(tmp_path) -> None:
    llm_client = RecordingSlideLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="环保主题 PPT", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：环保主题 PPT
来源 Job：{original.job_id}
页数：3
- 第 1 页：封面；要点：环保主题
- 第 2 页：背景与问题；要点：气候变化 / 资源压力
- 第 3 页：行动方案；要点：低碳出行 / 绿色消费

## 修改要求
第一页内容扩充一些，太简单

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    assert llm_client.generated_slides == [1]
    original_dir = settings.AIPPT_PROJECTS_PATH / original.job_id
    edited_dir = settings.AIPPT_PROJECTS_PATH / edited.job_id
    assert (edited_dir / "svg_output" / "slide_02.svg").read_text(encoding="utf-8") == (
        original_dir / "svg_output" / "slide_02.svg"
    ).read_text(encoding="utf-8")
    assert (edited_dir / "svg_output" / "slide_03.svg").read_text(encoding="utf-8") == (
        original_dir / "svg_output" / "slide_03.svg"
    ).read_text(encoding="utf-8")
    report = json.loads((edited_dir / "generation_report.json").read_text(encoding="utf-8"))
    assert report["planner"]["mode"] == "edit_current_ppt"
    first_slide = report["deck"]["slides"][0]
    assert first_slide["template"] == "three_cards"
    assert first_slide["page_rhythm"] == "dense"
    assert len(first_slide["body_items"]) >= 5
    assert first_slide["right_items"] == ["环保主题", "核心判断", "行动抓手"]
    assert "第一页内容扩充" not in (edited_dir / "svg_output" / "slide_01.svg").read_text(encoding="utf-8")


def test_aippt_current_ppt_edit_semantic_empty_slides_get_denser_body_text(tmp_path) -> None:
    llm_client = RecordingSlideLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="爱情主题 PPT", page_count=4, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：爱情主题 PPT
来源 Job：{original.job_id}
页数：4
- 第 1 页：爱情的多维定义：超越浪漫的三角构成；要点：三角理论 / 多维构成 / 关系基石
- 第 2 页：有效沟通：搭建爱的表达系统；要点：需求表达 / 情绪识别 / 冲突修复
- 第 3 页：共同成长：为关系建立长期目标；要点：共同目标 / 个体边界 / 成长节奏
- 第 4 页：信任与边界：构建稳定关系的底盘；要点：信任积累 / 边界协商 / 风险修复

## 修改要求
第一页第四页有点空，补充更多正文信息。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=4, style="clean_business")
    )
    service.run_job(edited.job_id)

    assert llm_client.generated_slides == [1, 4]
    original_dir = settings.AIPPT_PROJECTS_PATH / original.job_id
    edited_dir = settings.AIPPT_PROJECTS_PATH / edited.job_id
    assert (edited_dir / "svg_output" / "slide_02.svg").read_text(encoding="utf-8") == (
        original_dir / "svg_output" / "slide_02.svg"
    ).read_text(encoding="utf-8")
    assert (edited_dir / "svg_output" / "slide_03.svg").read_text(encoding="utf-8") == (
        original_dir / "svg_output" / "slide_03.svg"
    ).read_text(encoding="utf-8")

    report = json.loads((edited_dir / "generation_report.json").read_text(encoding="utf-8"))
    assert report["deck"]["body_density"] == "dense"
    first_slide = report["deck"]["slides"][0]
    fourth_slide = report["deck"]["slides"][3]
    assert first_slide["template"] == "three_cards"
    assert fourth_slide["template"] == "three_cards"
    assert first_slide["page_rhythm"] == "dense"
    assert fourth_slide["page_rhythm"] == "dense"
    assert len(first_slide["body_items"]) >= 6
    assert len(fourth_slide["body_items"]) >= 6
    assert any("三角理论" in item and len(item) > 30 for item in first_slide["body_items"])
    assert any("边界" in item and len(item) > 30 for item in fourth_slide["body_items"])
    assert first_slide["right_items"] == ["三角理论", "多维构成", "关系基石"]
    assert fourth_slide["right_items"] == ["信任积累", "边界协商", "风险修复"]


def test_aippt_current_ppt_edit_replaces_target_slide_text(tmp_path) -> None:
    llm_client = RecordingSlideLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="潮玩主题 PPT", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：潮玩主题 PPT
来源 Job：{original.job_id}
页数：3
- 第 1 页：潮玩市场：从收藏到社交的消费升级；要点：盲盒经济 / 设计师玩具 / 跨界联名
- 第 2 页：用户痛点：同质化与情感缺失；要点：同质化 vs 个性化 / 外观 vs 情感
- 第 3 页：解决方案：IP全链路孵化平台；要点：IP设计引擎 / 数字藏品系统

## 修改要求
第一页文字全换掉，改成一句话：这是自测验证文字

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    assert llm_client.generated_slides == [1]
    original_dir = settings.AIPPT_PROJECTS_PATH / original.job_id
    edited_dir = settings.AIPPT_PROJECTS_PATH / edited.job_id
    assert (edited_dir / "svg_output" / "slide_02.svg").read_text(encoding="utf-8") == (
        original_dir / "svg_output" / "slide_02.svg"
    ).read_text(encoding="utf-8")
    report = json.loads((edited_dir / "generation_report.json").read_text(encoding="utf-8"))
    first_slide = report["deck"]["slides"][0]
    assert first_slide["title"] == "这是自测验证文字"
    assert first_slide["right_items"] == ["这是自测验证文字"]
    assert "潮玩市场" not in json.dumps(first_slide, ensure_ascii=False)
    assert "第一页文字全换掉" not in json.dumps(first_slide, ensure_ascii=False)


def test_aippt_current_ppt_edit_adds_new_slide_and_renumbers_deck(tmp_path) -> None:
    llm_client = RecordingSlideLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="AI客服周报", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：AI客服周报
来源 Job：{original.job_id}
页数：3
- 第 1 页：AI客服周报；要点：问题分类统计 / 响应时效分析 / 客户满意度
- 第 2 页：客户问题分布；要点：账户42% / 支付28% / 使用18%
- 第 3 页：下周优化计划；要点：周一完成方案设计 / 周三开发联调 / 周五上线验证

## 修改要求
在第2页后增加一页，标题叫「处理策略与负责人」，内容包括分层处理、负责人、完成时限。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    result = service.get_job(edited.job_id)
    report = json.loads((settings.AIPPT_PROJECTS_PATH / edited.job_id / "generation_report.json").read_text(encoding="utf-8"))
    assert result.page_count == 4
    assert report["deck"]["page_count"] == 4
    assert [slide["slide_number"] for slide in report["deck"]["slides"]] == [1, 2, 3, 4]
    assert [slide["title"] for slide in report["deck"]["slides"]] == [
        "AI客服周报",
        "客户问题分布",
        "处理策略与负责人",
        "下周优化计划",
    ]
    assert report["deck"]["slides"][2]["body_items"]
    assert "分层处理" in json.dumps(report["deck"]["slides"][2], ensure_ascii=False)
    assert llm_client.generated_slides == [1, 2, 3, 4]


def test_aippt_current_ppt_edit_deletes_slide_and_renumbers_deck(tmp_path) -> None:
    llm_client = RecordingSlideLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="AI客服周报", page_count=4, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：AI客服周报
来源 Job：{original.job_id}
页数：4
- 第 1 页：AI客服周报；要点：问题分类统计 / 响应时效分析 / 客户满意度
- 第 2 页：客户问题分布；要点：账户42% / 支付28% / 使用18%
- 第 3 页：重复背景说明；要点：旧口径 / 重复信息 / 临时备注
- 第 4 页：下周优化计划；要点：周一完成方案设计 / 周三开发联调 / 周五上线验证

## 修改要求
删除第3页，后面的页码顺延。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=4, style="clean_business")
    )
    service.run_job(edited.job_id)

    result = service.get_job(edited.job_id)
    report = json.loads((settings.AIPPT_PROJECTS_PATH / edited.job_id / "generation_report.json").read_text(encoding="utf-8"))
    assert result.page_count == 3
    assert report["deck"]["page_count"] == 3
    assert [slide["slide_number"] for slide in report["deck"]["slides"]] == [1, 2, 3]
    assert [slide["title"] for slide in report["deck"]["slides"]] == [
        "AI客服周报",
        "客户问题分布",
        "下周优化计划",
    ]
    assert "重复背景说明" not in json.dumps(report["deck"]["slides"], ensure_ascii=False)
    assert llm_client.generated_slides == [1, 2, 3]


def test_aippt_current_ppt_edit_clears_target_slide_content_without_changing_page_count(tmp_path) -> None:
    llm_client = RecordingSlideLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="AI客服周报", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：AI客服周报
来源 Job：{original.job_id}
页数：3
- 第 1 页：AI客服周报；要点：问题分类统计 / 响应时效分析 / 客户满意度
- 第 2 页：客户问题分布；要点：账户42% / 支付28% / 使用18%
- 第 3 页：下周优化计划；要点：周一完成方案设计 / 周三开发联调 / 周五上线验证

## 修改要求
删除第2页内容，保留这一页位置。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    result = service.get_job(edited.job_id)
    report = json.loads((settings.AIPPT_PROJECTS_PATH / edited.job_id / "generation_report.json").read_text(encoding="utf-8"))
    assert result.page_count == 3
    assert report["deck"]["page_count"] == 3
    assert llm_client.generated_slides == [2]
    second_slide = report["deck"]["slides"][1]
    assert second_slide["title"] == "客户问题分布"
    assert second_slide["body_items"] == ["客户问题分布：已按要求删除原正文内容，可在此页重新补充新的说明。"]
    assert "账户42%" not in json.dumps(second_slide, ensure_ascii=False)


def test_aippt_current_ppt_edit_replaces_target_slide_title(tmp_path) -> None:
    llm_client = RecordingSlideLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="AI客服周报", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：AI客服周报
来源 Job：{original.job_id}
页数：3
- 第 1 页：AI客服周报；要点：问题分类统计 / 响应时效分析 / 客户满意度
- 第 2 页：客户问题分布；要点：账户42% / 支付28% / 使用18%
- 第 3 页：下周优化计划；要点：周一完成方案设计 / 周三开发联调 / 周五上线验证

## 修改要求
只把第2页标题改成「高频问题与处理效率」，其他页面和内容保持不变。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    assert llm_client.generated_slides == [2]
    report = json.loads((settings.AIPPT_PROJECTS_PATH / edited.job_id / "generation_report.json").read_text(encoding="utf-8"))
    assert report["deck"]["page_count"] == 3
    assert [slide["title"] for slide in report["deck"]["slides"]] == [
        "AI客服周报",
        "高频问题与处理效率",
        "下周优化计划",
    ]
    assert "其他页面" not in json.dumps(report["deck"]["slides"][1], ensure_ascii=False)


def test_aippt_current_ppt_edit_patches_target_slide_svg_without_regenerating(tmp_path) -> None:
    llm_client = ThemeAwareRecordingLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="动漫产业趋势", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    original_dir = settings.AIPPT_PROJECTS_PATH / original.job_id
    original_slide = (original_dir / "svg_output" / "slide_01.svg").read_text(encoding="utf-8")
    patched_original_slide = original_slide.replace("Slide 1", "全球动漫市场机会")
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：动漫产业趋势
来源 Job：{original.job_id}
页数：3
- 第 1 页：Slide 1；要点：亚洲增长 / IP商业化
- 第 2 页：Slide 2；要点：AI辅助 / 实时渲染
- 第 3 页：Slide 3；要点：会员订阅 / 衍生品

## 修改要求
把第一页标题改成「全球动漫市场机会」，其他结构不要动。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    edited_dir = settings.AIPPT_PROJECTS_PATH / edited.job_id
    assert llm_client.generated_slides == []
    assert (edited_dir / "svg_output" / "slide_01.svg").read_text(encoding="utf-8") == patched_original_slide


def test_aippt_current_ppt_edit_patches_free_design_svg_without_regenerating(tmp_path) -> None:
    llm_client = ThemeAwareRecordingLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="自由设计动漫趋势", page_count=3, style="clean_business", design_mode="free_design")
    )
    service.run_job(original.job_id)
    original_dir = settings.AIPPT_PROJECTS_PATH / original.job_id
    source_slide = (original_dir / "svg_output" / "slide_01.svg").read_text(encoding="utf-8")
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：自由设计动漫趋势
来源 Job：{original.job_id}
页数：3
- 第 1 页：Slide 1；要点：亚洲增长 / IP商业化
- 第 2 页：Slide 2；要点：AI辅助 / 实时渲染
- 第 3 页：Slide 3；要点：会员订阅 / 衍生品

## 修改要求
把第一页标题改成「自由设计新版标题」，其他结构不要动。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business", design_mode="free_design")
    )
    service.run_job(edited.job_id)

    edited_dir = settings.AIPPT_PROJECTS_PATH / edited.job_id
    report = json.loads((edited_dir / "generation_report.json").read_text(encoding="utf-8"))
    assert llm_client.generated_slides == []
    assert report["deck"]["design_mode"] == "free_design"
    assert report["deck"]["execution_mode"] == "free_design"
    assert (edited_dir / "svg_output" / "slide_01.svg").read_text(encoding="utf-8") == source_slide.replace("Slide 1", "自由设计新版标题")


def test_aippt_current_ppt_edit_keeps_source_deck_theme(tmp_path) -> None:
    llm_client = ThemeAwareRecordingLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="动漫产业趋势", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：动漫产业趋势
来源 Job：{original.job_id}
页数：3
- 第 1 页：全球动漫市场持续扩张；要点：亚洲增长 / IP商业化
- 第 2 页：技术革新重塑流程；要点：AI辅助 / 实时渲染
- 第 3 页：商业模式升级；要点：会员订阅 / 衍生品

## 修改要求
把第一页标题改成「全球动漫市场机会」，其他结构不要动。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    edited_dir = settings.AIPPT_PROJECTS_PATH / edited.job_id
    report = json.loads((edited_dir / "generation_report.json").read_text(encoding="utf-8"))
    slide_svg = (edited_dir / "svg_output" / "slide_01.svg").read_text(encoding="utf-8")
    assert report["deck"]["theme_colors"]["primary"] == "#7C3AED"
    assert "#7C3AED" in slide_svg
    assert "#2563EB" not in slide_svg


def test_aippt_current_ppt_edit_uses_svg_theme_when_metadata_is_stale(tmp_path) -> None:
    llm_client = ThemeAwareRecordingLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    original = service.create_job_from_request(
        PPTGenerationRequest(topic="动漫产业趋势", page_count=3, style="clean_business")
    )
    service.run_job(original.job_id)
    original_dir = settings.AIPPT_PROJECTS_PATH / original.job_id
    stale_theme = {
        "bg": "#F8FAFC",
        "panel": "#FFFFFF",
        "primary": "#2563EB",
        "accent": "#DBEAFE",
        "secondary_accent": "#EFF6FF",
        "text": "#0F172A",
        "text_secondary": "#475569",
        "border": "#E2E8F0",
    }
    metadata_path = original_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["theme_colors"] = stale_theme
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    report_path = original_dir / "generation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["deck"]["theme_colors"] = stale_theme
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    llm_client.generated_slides.clear()

    edit_source = f"""
## 当前 PPT
标题：动漫产业趋势
来源 Job：{original.job_id}
页数：3
- 第 1 页：全球动漫市场持续扩张；要点：亚洲增长 / IP商业化
- 第 2 页：技术革新重塑流程；要点：AI辅助 / 实时渲染
- 第 3 页：商业模式升级；要点：会员订阅 / 衍生品

## 修改要求
把第一页标题改成「全球动漫市场机会」，其他结构不要动。

## 生成要求
基于上面的当前 PPT 继续修改，输出完整可导出的 PPT。
""".strip()
    edited = service.create_job_from_request(
        PPTGenerationRequest(topic=edit_source, page_count=3, style="clean_business")
    )
    service.run_job(edited.job_id)

    edited_dir = settings.AIPPT_PROJECTS_PATH / edited.job_id
    report = json.loads((edited_dir / "generation_report.json").read_text(encoding="utf-8"))
    assert report["deck"]["theme_colors"]["primary"] == "#7C3AED"


def test_aippt_service_retries_invalid_svg_before_writing_slide(tmp_path) -> None:
    llm_client = RetryThenValidLLMClient()
    service, settings = _build_service(tmp_path, llm_client=llm_client)

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=1, style="clean_business")
    )
    service.run_job(job.job_id)

    slide_svg = (settings.AIPPT_PROJECTS_PATH / job.job_id / "svg_output" / "slide_01.svg").read_text(
        encoding="utf-8"
    )
    assert llm_client.slide_attempts == 2
    assert "<foreignObject" not in slide_svg
    assert 'viewBox="0 0 1280 720"' in slide_svg


def test_template_mode_skips_pending_image_generation_even_when_resources_exist(tmp_path) -> None:
    image_generator = RecordingImageGenerator()
    service, _ = _build_service(
        tmp_path,
        llm_client=PendingImageLLMClient(),
        image_generator=image_generator,
    )

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=1, style="ai_image_clean", design_mode="template")
    )
    service.run_job(job.job_id)

    assert service.get_job(job.job_id).status == "done"
    assert image_generator.called is False


def test_free_design_generates_non_image_slides_while_image_generation_runs(tmp_path) -> None:
    image_started = threading.Event()
    image_done = threading.Event()
    allow_image_finish = threading.Event()
    llm_client = ParallelFreeDesignLLMClient(image_done, allow_image_finish)
    image_generator = BlockingImageGenerator(image_started, image_done, allow_image_finish)
    service, _ = _build_service(tmp_path, llm_client=llm_client, image_generator=image_generator)

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=3, style="ai_image_editorial", design_mode="free_design")
    )
    service.run_job(job.job_id)

    assert service.get_job(job.job_id).status == "done"
    assert image_started.is_set()
    assert (2, False) in llm_client.slide_events
    assert (1, True) in llm_client.slide_events


def test_aippt_service_persists_image_uploads_and_records_image_resources(tmp_path) -> None:
    service, settings = _build_service(tmp_path)
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest-image-bytes"

    job = service.create_job_from_request(
        PPTGenerationRequest(topic="AI PPT", page_count=2, style="ai_image_clean"),
        image_uploads=[("Cover Hero 01.PNG", png_bytes)],
    )
    service.run_job(job.job_id)

    project_dir = settings.AIPPT_PROJECTS_PATH / job.job_id
    image_path = project_dir / "images" / "Cover_Hero_01.png"
    prompt_path = project_dir / "images" / "image_prompts.md"
    report_path = project_dir / "generation_report.json"

    assert image_path.exists()
    assert image_path.read_bytes() == png_bytes

    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert "Cover_Hero_01.png" in prompt_text
    assert "Existing" in prompt_text
    assert "User-provided image" in prompt_text

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["images"]["resources"] == [
        {
            "filename": "Cover_Hero_01.png",
            "dimensions": "Unknown",
            "purpose": "User-provided image",
            "type": "Photography",
            "status": "Existing",
            "generation_description": "-",
        }
    ]
    assert report["images"]["prompt_document"].endswith("/images/image_prompts.md")


def test_aippt_service_rejects_invalid_image_uploads(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="Unsupported image file type"):
        service.create_job_from_request(
            PPTGenerationRequest(topic="AI PPT", page_count=1, style="ai_image_clean"),
            image_uploads=[
                ("cover.gif", b"GIF89a"),
            ],
        )


def test_aippt_service_rejects_invalid_image_bytes(tmp_path) -> None:
    service, _ = _build_service(tmp_path)

    with pytest.raises(ValueError, match="Invalid image file content"):
        service.create_job_from_request(
            PPTGenerationRequest(topic="AI PPT", page_count=1, style="ai_image_clean"),
            image_uploads=[
                ("cover.png", b"not-a-real-png"),
            ],
        )
