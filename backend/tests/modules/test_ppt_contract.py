from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.container import register_routers
from app.modules.ppt.dependencies import get_ppt_service
from app.modules.ppt.repository import PptRepository
from app.modules.ppt.schemas import PptDeckSchema
from app.modules.ppt.service import PptService


class FakeDeepSeekClient:
    def __init__(
        self,
        *,
        configured: bool = True,
        create_response: dict[str, object] | None = None,
        modify_response: dict[str, object] | None = None,
    ) -> None:
        self.configured = configured
        self.create_response = create_response
        self.modify_response = modify_response
        self.calls: list[dict[str, object]] = []

    def is_configured(self) -> bool:
        return self.configured

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 60,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "timeout": timeout,
                "max_tokens": max_tokens,
            }
        )
        payload = json.loads(user_prompt)
        if "instruction" in payload:
            if self.modify_response is not None:
                return self.modify_response
            deck = payload["deck"]
            target_slide_id = payload.get("slide_id") or deck["slides"][0]["slide_id"]
            slides = []
            for slide in deck["slides"]:
                if slide["slide_id"] != target_slide_id:
                    continue
                slides.append(
                    {
                        **slide,
                        "title": "下周计划" if "标题" in payload["instruction"] else slide["title"],
                        "body": [*slide["body"], payload["instruction"]],
                    }
                )
            theme = "business" if "商务" in payload["instruction"] else deck["theme"]
            theme = "apple_white" if "简约" in payload["instruction"] else theme
            return {"theme": theme, "slides": slides}

        if self.create_response is not None:
            return self.create_response

        preferences = payload["preferences"]
        count = preferences["slides_limit"]
        return {
            "title": "DeepSeek 生成的项目总结",
            "theme": preferences["theme"],
            "slides": [
                {
                    "title": f"DeepSeek 第 {index + 1} 页",
                    "body": [f"模型生成要点 {index + 1}", payload["content"]],
                    "notes": "DeepSeek speaker notes",
                    "images": [],
                }
                for index in range(count)
            ],
        }


def _build_client(llm_client: FakeDeepSeekClient | None = None) -> TestClient:
    app = FastAPI()
    register_routers(app)
    fake_llm = llm_client or FakeDeepSeekClient()
    service = PptService(PptRepository(), llm_client=fake_llm)
    app.dependency_overrides[get_ppt_service] = lambda: service
    app.state.fake_llm = fake_llm
    app.state.ppt_service = service
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_ppt_state(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GENERATED_ROOT", str(tmp_path))
    get_settings.cache_clear()

    from app.modules.ppt import dependencies as ppt_dependencies

    ppt_dependencies._ppt_service = None
    yield tmp_path
    ppt_dependencies._ppt_service = None
    get_settings.cache_clear()


def test_create_ppt_deck_requires_configured_deepseek() -> None:
    client = _build_client(FakeDeepSeekClient(configured=False))

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "Q2 复盘：收入增长 32%。",
            "preferences": {"theme": "tech", "slides_limit": 3},
        },
    )

    assert response.status_code == 503
    assert "DeepSeek" in response.json()["detail"]


def test_create_ppt_deck_uses_deepseek_json() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "Q2 复盘：收入增长 32%，新增企业客户 18 家，继续投入自动化交付。",
            "preferences": {
                "theme": "tech",
                "slides_limit": 3,
                "author": "Felix",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    deck = payload["data"]
    assert deck["theme"] == "apple_black"
    assert deck["version"] == 1
    assert deck["author"] == "Felix"
    assert deck["history"][0]["action"] == "create"
    assert len(deck["slides"]) == 3
    assert deck["title"] == "DeepSeek 生成的项目总结"
    assert deck["slides"][0]["title"] == "DeepSeek 第 1 页"
    assert all(slide["version"] == 1 for slide in deck["slides"])
    assert all(slide["id"] == slide["slide_id"] for slide in deck["slides"])
    assert all(slide["theme"] == "apple_black" for slide in deck["slides"])
    assert all(slide["author"] == "Felix" for slide in deck["slides"])
    assert all("last_modified" in slide for slide in deck["slides"])
    assert deck["html"].count("<section") == 3
    assert "模型生成要点" in deck["html"]
    assert len(client.app.state.fake_llm.calls) == 1


def test_create_ppt_deck_preserves_multiple_layouts_and_layout_fields() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "多布局演示",
                "theme": "business",
                "slides": [
                    {
                        "layout": "cover",
                        "title": "飞书 AI 校园挑战赛",
                        "subtitle": "联测阶段汇报",
                        "kicker": "内部试验版",
                    },
                    {
                        "layout": "two_column",
                        "title": "技术链路",
                        "left_title": "输入侧",
                        "right_title": "输出侧",
                        "left": ["飞书消息", "调起后端服务"],
                        "right": ["DeepSeek 生成 deck", "HTML 与 PPTX 导出"],
                    },
                    {
                        "layout": "timeline",
                        "title": "里程碑",
                        "items": ["需求对齐", "联调完成", "准备答辩"],
                    },
                    {
                        "layout": "metrics",
                        "title": "关键指标",
                        "metrics": [
                            {"label": "通过率", "value": "98%", "note": "核心流程"},
                            {"label": "响应", "value": "<2s"},
                        ],
                    },
                    {
                        "layout": "summary",
                        "title": "下一步",
                        "body": ["固化模板", "补充监控"],
                        "actions": ["完成压测", "准备演示"],
                    },
                    {
                        "layout": "bullets",
                        "title": "补充说明",
                        "body": ["保留普通 bullet 页"],
                        "notes": "需要兼容旧结构",
                    },
                ],
            }
        )
    )

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "请整理为多布局的项目汇报。",
            "preferences": {"theme": "business", "slides_limit": 6},
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    assert deck["theme"] == "business"

    assert [slide["layout"] for slide in deck["slides"]] == [
        "cover",
        "two_column",
        "timeline",
        "metrics",
        "summary",
        "bullets",
    ]
    assert deck["slides"][0]["subtitle"] == "联测阶段汇报"
    assert deck["slides"][0]["kicker"] == "内部试验版"
    assert deck["slides"][1]["left_title"] == "输入侧"
    assert deck["slides"][1]["right_title"] == "输出侧"
    assert deck["slides"][1]["left"] == ["飞书消息", "调起后端服务"]
    assert deck["slides"][1]["right"] == ["DeepSeek 生成 deck", "HTML 与 PPTX 导出"]
    assert deck["slides"][2]["items"] == ["需求对齐", "联调完成", "准备答辩"]
    assert deck["slides"][3]["metrics"] == [
        {"label": "通过率", "value": "98%", "note": "核心流程"},
        {"label": "响应", "value": "<2s", "note": None},
    ]
    assert deck["slides"][4]["actions"] == ["完成压测", "准备演示"]


def test_create_ppt_deck_falls_back_unknown_layout_to_bullets() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "布局兜底",
                "theme": "tech",
                "slides": [
                    {
                        "layout": "radar",
                        "title": "未知版式",
                        "body": ["保底为 bullets"],
                    }
                ],
            }
        )
    )

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "给我一页测试未知布局。",
            "preferences": {"theme": "tech", "slides_limit": 1},
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    assert deck["slides"][0]["layout"] == "bullets"
    assert deck["slides"][0]["body"] == ["保底为 bullets"]


def test_create_ppt_deck_strips_markdown_from_title_body_and_notes() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "**季度复盘** [总览](https://example.com)",
                "theme": "tech",
                "slides": [
                    {
                        "layout": "cover",
                        "title": "**前端** 进展",
                        "subtitle": "**阶段** [回顾](https://example.com)",
                        "kicker": "`Sprint 4`",
                    },
                    {
                        "layout": "two_column",
                        "title": "**双栏** 拆解",
                        "left_title": "__输入__",
                        "right_title": "*输出*",
                        "left": [
                            "**前端** 能力补齐",
                            "[链接](https://example.com) 已同步",
                        ],
                        "right": [
                            "- `交付` 节点明确",
                            "1. _风险_ 收敛",
                        ],
                        "notes": "__备注__：联系 [接口人](https://example.com)",
                        "images": [],
                    },
                    {
                        "layout": "metrics",
                        "title": "**指标** 看板",
                        "metrics": [
                            {
                                "label": "__覆盖率__",
                                "value": "`98%`",
                                "note": "[核心流程](https://example.com)",
                            }
                        ],
                        "notes": "__备注__：联系 [接口人](https://example.com)",
                        "images": [],
                    }
                ],
            }
        )
    )

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "请整理一个三页的项目复盘。",
            "preferences": {
                "theme": "tech",
                "slides_limit": 3,
            },
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]

    assert deck["title"] == "季度复盘 总览"
    assert deck["slides"][0]["title"] == "前端 进展"
    assert deck["slides"][0]["subtitle"] == "阶段 回顾"
    assert deck["slides"][0]["kicker"] == "Sprint 4"
    assert deck["slides"][1]["left_title"] == "输入"
    assert deck["slides"][1]["right_title"] == "输出"
    assert deck["slides"][1]["left"] == [
        "前端 能力补齐",
        "链接 已同步",
    ]
    assert deck["slides"][1]["right"] == [
        "交付 节点明确",
        "风险 收敛",
    ]
    assert deck["slides"][1]["notes"] == "备注：联系 接口人"
    assert deck["slides"][2]["metrics"] == [
        {"label": "覆盖率", "value": "98%", "note": "核心流程"}
    ]
    assert "**" not in json.dumps(deck, ensure_ascii=False)
    assert "[" not in deck["html"]
    assert "](" not in deck["html"]
    assert "**" not in deck["html"]


def test_create_ppt_deck_renders_layout_specific_html_classes() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "HTML 布局测试",
                "theme": "minimal",
                "slides": [
                    {"layout": "cover", "title": "封面", "subtitle": "试验版"},
                    {
                        "layout": "section_divider",
                        "title": "第二章",
                        "subtitle": "系统方案",
                        "kicker": "Architecture",
                    },
                    {
                        "layout": "quote",
                        "title": "关键结论",
                        "quote": "先把结构做对，视觉才会稳。",
                        "source": "项目复盘",
                    },
                    {
                        "layout": "two_column",
                        "title": "双栏",
                        "left_title": "左侧",
                        "right_title": "右侧",
                        "left": ["A"],
                        "right": ["B"],
                    },
                    {"layout": "timeline", "title": "时间线", "items": ["一", "二"]},
                    {
                        "layout": "process",
                        "title": "流程",
                        "items": ["采集输入", "结构生成", "导出复核"],
                    },
                    {
                        "layout": "comparison",
                        "title": "方案对比",
                        "left_title": "旧版",
                        "right_title": "新版",
                        "left": ["布局较少"],
                        "right": ["结构更多"],
                    },
                    {
                        "layout": "metrics",
                        "title": "指标",
                        "metrics": [{"label": "成功率", "value": "95%"}],
                    },
                    {
                        "layout": "matrix",
                        "title": "优先级矩阵",
                        "quadrants": [
                            {"title": "高价值高紧急", "body": "导出链路"},
                            {"title": "高价值低紧急", "body": "模板沉淀"},
                            {"title": "低价值高紧急", "body": "演示修饰"},
                            {"title": "低价值低紧急", "body": "历史兼容说明"},
                        ],
                    },
                    {
                        "layout": "architecture",
                        "title": "架构总览",
                        "blocks": [
                            {"title": "输入层", "body": "飞书消息与文档"},
                            {"title": "编排层", "body": "PPT service"},
                            {"title": "输出层", "body": "HTML / PPTX"},
                        ],
                    },
                ],
            }
        )
    )

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "text",
            "content": "做一个十页多布局测试。",
            "preferences": {"theme": "minimal", "slides_limit": 10},
        },
    )

    assert response.status_code == 200
    html = response.json()["data"]["html"]
    assert "layout-cover" in html
    assert "layout-section-divider" in html
    assert "layout-quote" in html
    assert "layout-two-column" in html
    assert "layout-timeline" in html
    assert "layout-process" in html
    assert "layout-comparison" in html
    assert "layout-metrics" in html
    assert "layout-matrix" in html
    assert "layout-architecture" in html


def test_create_ppt_deck_uses_dedicated_border_color_in_apple_white_html() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "苹果白风边框测试",
                "theme": "apple_white",
                "slides": [
                    {
                        "layout": "two_column",
                        "title": "双栏",
                        "left_title": "左侧",
                        "right_title": "右侧",
                        "left": ["A"],
                        "right": ["B"],
                    }
                ],
            }
        )
    )

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "生成一页苹果白主题的结构页。",
            "preferences": {"theme": "apple_white", "slides_limit": 1},
        },
    )

    assert response.status_code == 200
    html = response.json()["data"]["html"]
    assert "theme-apple_white" in html
    assert "--component:#4A90E2" in html
    assert "--line:#D9E2F0" in html
    assert "--card:#FFFFFF" in html
    assert "border:1px solid var(--line)" in html


def test_create_ppt_deck_normalizes_timeline_objects_and_leading_bullets() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "结构清洗测试",
                "theme": "business",
                "slides": [
                    {
                        "layout": "timeline",
                        "title": "里程碑",
                        "items": [
                            {
                                "date": "2024 Q1",
                                "title": "启动项目",
                                "description": "完成范围定义",
                            },
                            "· 2024 Q2 完成联调",
                        ],
                    },
                    {
                        "layout": "two_column",
                        "title": "风险拆解",
                        "left_title": "输入",
                        "right_title": "输出",
                        "left": ["• 风险识别", "- 范围确认"],
                        "right": ["1. 联调排期", "· 交付验收"],
                    },
                ],
            }
        )
    )

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "请生成两页项目推进汇报。",
            "preferences": {"theme": "business", "slides_limit": 2},
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]

    assert deck["slides"][0]["items"] == [
        "2024 Q1 | 启动项目 | 完成范围定义",
        "2024 Q2 完成联调",
    ]
    assert deck["slides"][1]["left"] == ["风险识别", "范围确认"]
    assert deck["slides"][1]["right"] == ["联调排期", "交付验收"]
    assert "{'date':" not in deck["html"]
    assert "2024 Q1 | 启动项目 | 完成范围定义" in deck["html"]
    assert ">• 风险识别<" not in deck["html"]
    assert ">- 范围确认<" not in deck["html"]
    assert ">1. 联调排期<" not in deck["html"]
    assert ">· 交付验收<" not in deck["html"]


def test_create_ppt_deck_supports_new_layout_payloads_and_component_items() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "扩展布局测试",
                "theme": "eco",
                "slides": [
                    {
                        "layout": "section_divider",
                        "title": "第三章",
                        "subtitle": "平台能力扩展",
                        "kicker": "Platform",
                    },
                    {
                        "layout": "quote",
                        "title": "结论",
                        "quote": "组件化比把所有内容塞进白框里更清晰。",
                        "source": "设计评审",
                    },
                    {
                        "layout": "process",
                        "title": "实施流程",
                        "items": [
                            {"title": "建模", "body": "定义新布局 schema"},
                            {"title": "渲染", "body": "生成 HTML 组件"},
                            {"title": "导出", "body": "输出可编辑 PPTX"},
                        ],
                    },
                    {
                        "layout": "matrix",
                        "title": "能力矩阵",
                        "quadrants": [
                            {"title": "高价值高紧急", "body": "section / quote"},
                            {"title": "高价值低紧急", "body": "architecture"},
                            {"title": "低价值高紧急", "body": "文案润色"},
                            {"title": "低价值低紧急", "body": "额外动画"},
                        ],
                    },
                    {
                        "layout": "architecture",
                        "title": "系统架构",
                        "blocks": [
                            {"title": "LLM", "body": "DeepSeek 生成结构"},
                            {"title": "Backend", "body": "标准化 deck 数据"},
                            {"title": "Exporter", "body": "PPTX 可编辑导出"},
                        ],
                    },
                ],
            }
        )
    )

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "请整理成一套结构化项目汇报。",
            "preferences": {"theme": "eco", "slides_limit": 5},
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]

    assert [slide["layout"] for slide in deck["slides"]] == [
        "section_divider",
        "quote",
        "process",
        "matrix",
        "architecture",
    ]
    assert deck["slides"][0]["subtitle"] == "平台能力扩展"
    assert deck["slides"][0]["kicker"] == "Platform"
    assert deck["slides"][1]["quote"] == "组件化比把所有内容塞进白框里更清晰。"
    assert deck["slides"][1]["source"] == "设计评审"
    assert deck["slides"][2]["items"] == [
        "建模 | 定义新布局 schema",
        "渲染 | 生成 HTML 组件",
        "导出 | 输出可编辑 PPTX",
    ]
    assert [item["title"] for item in deck["slides"][3]["quadrants"]] == [
        "高价值高紧急",
        "高价值低紧急",
        "低价值高紧急",
        "低价值低紧急",
    ]
    assert [item["body"] for item in deck["slides"][3]["quadrants"]] == [
        "section / quote",
        "architecture",
        "文案润色",
        "额外动画",
    ]
    assert [item["title"] for item in deck["slides"][4]["blocks"]] == [
        "LLM",
        "Backend",
        "Exporter",
    ]
    assert [item["body"] for item in deck["slides"][4]["blocks"]] == [
        "DeepSeek 生成结构",
        "标准化 deck 数据",
        "PPTX 可编辑导出",
    ]
    assert "quote-mark" in deck["html"]
    assert "process-step" in deck["html"]
    assert "matrix-grid" in deck["html"]
    assert "architecture-block" in deck["html"]


def test_create_ppt_deck_prompt_mentions_extended_layout_catalog() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "text",
            "content": "整理一份介绍平台架构和结论的演示文稿。",
            "preferences": {"theme": "business", "slides_limit": 3},
        },
    )

    assert response.status_code == 200
    prompt = client.app.state.fake_llm.calls[0]["system_prompt"]
    assert "section_divider" in prompt
    assert "quote(" in prompt
    assert "comparison(" in prompt
    assert "process(" in prompt
    assert "matrix(" in prompt
    assert "architecture(" in prompt


def test_create_ppt_deck_prefers_slide_count_parsed_from_message() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "请生成 3 页内部汇报 PPT，聚焦本周进展和风险。",
            "preferences": {
                "theme": "tech",
                "slides_limit": 6,
            },
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    llm_payload = json.loads(client.app.state.fake_llm.calls[0]["user_prompt"])

    assert llm_payload["preferences"]["slides_limit"] == 3
    assert len(deck["slides"]) == 3
    assert deck["html"].count("<section") == 3


def test_create_ppt_deck_uses_upper_bound_for_slide_count_range_and_clamps_to_schema_limit() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "输出 8-15 页季度复盘 PPT，突出收入趋势和团队效率。",
            "preferences": {
                "theme": "business",
                "slides_limit": 4,
            },
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    llm_payload = json.loads(client.app.state.fake_llm.calls[0]["user_prompt"])

    assert llm_payload["preferences"]["slides_limit"] == 15
    assert len(deck["slides"]) == 15
    assert deck["html"].count("<section") == 15


def test_create_ppt_deck_clamps_message_slide_count_to_schema_limit() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "输出 8-30 页季度复盘 PPT，突出收入趋势和团队效率。",
            "preferences": {
                "theme": "business",
                "slides_limit": 4,
            },
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    llm_payload = json.loads(client.app.state.fake_llm.calls[0]["user_prompt"])

    assert llm_payload["preferences"]["slides_limit"] == 20
    assert len(deck["slides"]) == 20
    assert deck["html"].count("<section") == 20


def test_create_ppt_deck_supports_chinese_numeral_slide_count() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "text",
            "content": "做一份六页汇报，说明 AI 助手项目的阶段成果。",
            "preferences": {
                "theme": "minimal",
                "slides_limit": 2,
            },
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    llm_payload = json.loads(client.app.state.fake_llm.calls[0]["user_prompt"])

    assert llm_payload["preferences"]["slides_limit"] == 6
    assert len(deck["slides"]) == 6


@pytest.mark.parametrize(
    ("theme_name", "expected_theme"),
    [
        ("科技风", "apple_black"),
        ("商务风", "business"),
        ("简约风", "apple_white"),
        ("薄荷绿", "eco"),
        ("天空蓝", "academic"),
    ],
)
def test_create_ppt_deck_accepts_user_scheme_payload_with_chinese_theme(
    theme_name: str,
    expected_theme: str,
) -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat_record",
            "content": "今天团队讨论了项目进度，需要生成 PPT 总结。",
            "preferences": {
                "theme": theme_name,
                "slides_limit": 2,
            },
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    assert deck["type"] == "chat_record"
    assert deck["theme"] == expected_theme
    assert len(deck["slides"]) == 2


def test_modify_ppt_deck_increments_target_slide_version() -> None:
    client = _build_client()
    created = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "text",
            "content": "发布一份关于 AI 助手落地价值的三页演示文稿。",
            "preferences": {
                "theme": "minimal",
                "slides_limit": 3,
                "author": "Team Eko",
            },
        },
    ).json()["data"]

    target_slide = created["slides"][1]
    response = client.post(
        f"/api/v1/ppt/decks/{created['deck_id']}/modify",
        json={
            "instruction": "把这一页改成更强调 ROI 和交付效率的表达",
            "slide_id": target_slide["slide_id"],
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    updated_target = next(
        slide for slide in deck["slides"]
        if slide["slide_id"] == target_slide["slide_id"]
    )
    untouched = [
        slide for slide in deck["slides"]
        if slide["slide_id"] != target_slide["slide_id"]
    ]

    assert deck["version"] == 2
    assert deck["last_modified"] != created["last_modified"]
    assert updated_target["version"] == 2
    assert all(slide["version"] == 1 for slide in untouched)
    assert deck["history"][-1]["action"] == "modify"
    assert "ROI" in deck["html"]


def test_modify_can_update_target_slide_title() -> None:
    client = _build_client()
    created = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "text",
            "content": "第一页讲背景，第二页讲下周计划。",
            "preferences": {
                "theme": "minimal",
                "slides_limit": 2,
            },
        },
    ).json()["data"]
    target_slide = created["slides"][1]

    response = client.post(
        f"/api/v1/ppt/decks/{created['deck_id']}/modify",
        json={
            "instruction": "把第二页的标题改为“下周计划”",
            "slide_id": target_slide["id"],
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    updated_target = next(
        slide for slide in deck["slides"]
        if slide["id"] == target_slide["id"]
    )
    assert updated_target["title"] == "下周计划"
    assert "下周计划" in deck["html"]


def test_modify_can_use_current_deck_payload_after_service_restart() -> None:
    client = _build_client()
    created = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat_record",
            "content": "讨论记录：本周完成原型，下周推进联调。",
            "preferences": {
                "theme": "tech",
                "slides_limit": 2,
            },
        },
    ).json()["data"]

    from app.modules.ppt import dependencies as ppt_dependencies

    ppt_dependencies._ppt_service = None
    response = client.post(
        f"/api/v1/ppt/decks/{created['deck_id']}/modify",
        json={
            "instruction": "改成简约风，并突出下周联调风险",
            "current_deck": created,
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    assert deck["deck_id"] == created["deck_id"]
    assert deck["theme"] == "apple_white"
    assert deck["version"] == 2


def test_modify_can_switch_theme() -> None:
    client = _build_client()
    created = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "text",
            "content": "生成一份产品路线图演示稿。",
            "preferences": {
                "theme": "tech",
                "slides_limit": 2,
            },
        },
    ).json()["data"]

    response = client.post(
        f"/api/v1/ppt/decks/{created['deck_id']}/modify",
        json={
            "instruction": "整体改成商务风，并让措辞更稳健",
            "current_deck": created,
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]
    assert deck["theme"] == "business"
    assert "theme-business" in deck["html"]


def test_modify_ppt_deck_strips_markdown_from_updated_and_existing_content() -> None:
    client = _build_client(
        FakeDeepSeekClient(
            modify_response={
                "theme": "business",
                "slides": [
                    {
                        "slide_id": "slide_to_update",
                        "title": "**下周计划**",
                        "body": [
                            "[联调](https://example.com) 排期锁定",
                            "*风险* 跟踪",
                        ],
                        "notes": "__备注__：[Owner](https://example.com)",
                    }
                ],
            }
        )
    )
    created = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "text",
            "content": "生成一份两页项目周报。",
            "preferences": {
                "theme": "tech",
                "slides_limit": 2,
            },
        },
    ).json()["data"]

    created["title"] = "**历史总览**"
    created["slides"][0]["slide_id"] = "slide_to_update"
    created["slides"][0]["id"] = "slide_to_update"
    created["slides"][0]["title"] = "**旧标题**"
    created["slides"][0]["body"] = ["**旧内容**", "[历史链接](https://example.com)"]
    created["slides"][0]["notes"] = "__旧备注__"
    created["slides"][1]["title"] = "**保留页**"
    created["slides"][1]["body"] = ["*保留内容*"]
    created["slides"][1]["notes"] = "[保留备注](https://example.com)"
    client.app.state.ppt_service._repository.save(PptDeckSchema.model_validate(created))

    response = client.post(
        f"/api/v1/ppt/decks/{created['deck_id']}/modify",
        json={
            "instruction": "改成商务风，并更新第一页",
            "current_deck": created,
            "slide_id": "slide_to_update",
        },
    )

    assert response.status_code == 200
    deck = response.json()["data"]

    assert deck["title"] == "历史总览"
    assert deck["slides"][0]["title"] == "下周计划"
    assert deck["slides"][0]["body"] == ["联调 排期锁定", "风险 跟踪"]
    assert deck["slides"][0]["notes"] == "备注：Owner"
    assert deck["slides"][1]["title"] == "保留页"
    assert deck["slides"][1]["body"] == ["保留内容"]
    assert deck["slides"][1]["notes"] == "保留备注"
    assert "**" not in json.dumps(deck, ensure_ascii=False)
    assert "](" not in deck["html"]


def test_export_ppt_returns_generated_file_metadata(tmp_path: Path) -> None:
    client = _build_client(
        FakeDeepSeekClient(
            create_response={
                "title": "导出布局测试",
                "theme": "business",
                "slides": [
                    {
                        "layout": "cover",
                        "title": "导出封面",
                        "subtitle": "多布局",
                        "kicker": "实验版",
                    },
                    {
                        "layout": "two_column",
                        "title": "链路拆解",
                        "left_title": "输入",
                        "right_title": "输出",
                        "left": ["请求", "编排"],
                        "right": ["结构化 deck", "PPTX"],
                    },
                    {
                        "layout": "timeline",
                        "title": "阶段推进",
                        "items": ["启动", "联调", "验收"],
                    },
                    {
                        "layout": "metrics",
                        "title": "指标",
                        "metrics": [{"label": "通过率", "value": "98%"}],
                    },
                    {
                        "layout": "summary",
                        "title": "行动项",
                        "body": ["继续完善多布局"],
                        "actions": ["补齐更多测试"],
                    },
                ],
            }
        )
    )
    created = client.post(
        "/api/v1/ppt/decks",
        json={
            "type": "chat",
            "content": "把这段聊天整理成项目启动会 PPT。",
            "preferences": {
                "theme": "business",
                "slides_limit": 5,
            },
        },
    ).json()["data"]

    response = client.post(f"/api/v1/ppt/decks/{created['deck_id']}/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    export_data = payload["data"]
    assert export_data["deck_id"] == created["deck_id"]
    assert export_data["file_name"].endswith(".pptx")
    assert export_data["path"].endswith(".pptx")
    assert Path(export_data["path"]).exists()
    with zipfile.ZipFile(export_data["path"]) as archive:
        assert "[Content_Types].xml" in archive.namelist()


def test_list_ppt_themes_returns_expected_options() -> None:
    client = _build_client()

    response = client.get("/api/v1/ppt/themes")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"] == [
        {"theme_id": "business", "label": "business 商务风"},
        {"theme_id": "academic", "label": "academic 学术风"},
        {"theme_id": "apple_black", "label": "apple_black 苹果黑风"},
        {"theme_id": "apple_white", "label": "apple_white 苹果白风"},
        {"theme_id": "eco", "label": "eco 绿色环保风"},
    ]
