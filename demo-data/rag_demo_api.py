from __future__ import annotations

import hashlib
import json
import re
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, File, Form, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


DEMO_CONTENT = """# Eko RAG 编辑演示资料

这是一份用于验证知识库资料预览和编辑能力的演示文档。

## 核心场景

- 导入后可以直接预览正文。
- 可以少量编辑正文并保存。
- 可以全选替换整份资料内容。
- 保存正文后会重新索引，供 Agent 和检索使用。

## 检索关键词

RAG 编辑、资料预览、重新索引、飞书知识库、Eko 演示。"""


class RagFileCreateRequest(BaseModel):
    filename: str
    source: str | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagFileUpdateRequest(BaseModel):
    filename: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None
    content: str | None = None


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthRegisterRequest(BaseModel):
    display_name: str
    email: str
    password: str


class AuthUserUpdateRequest(BaseModel):
    display_name: str | None = None
    name_en: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    phone_ext: str | None = None
    location: str | None = None
    time_zone: str | None = None
    employee_id: str | None = None
    job_title: str | None = None
    department: str | None = None
    team: str | None = None
    reports_to: str | None = None
    joined_at: str | None = None
    bio: str | None = None
    languages: list[str] | None = None


class AuthPasswordUpdateRequest(BaseModel):
    current_password: str
    new_password: str


class FeishuLoginRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str | None = None


class BitableSourcePayload(BaseModel):
    workspace_id: str = "Feishu_demo_Eko"
    name: str
    base_id: str | None = None
    app_token: str | None = None
    table_id: str
    view_id: str | None = None
    purpose: str = "both"
    title_field: str | None = None
    summary_field: str | None = None
    url_field: str | None = None
    status_field: str | None = None
    type_field: str | None = None
    owner_field: str | None = None
    date_field: str | None = None
    field_mapping: dict[str, Any] = Field(default_factory=dict)


class BitableSourcePatch(BaseModel):
    name: str | None = None
    app_token: str | None = None
    view_id: str | None = None
    enabled: bool | None = None
    purpose: str | None = None
    title_field: str | None = None
    summary_field: str | None = None
    url_field: str | None = None
    status_field: str | None = None
    type_field: str | None = None
    owner_field: str | None = None
    date_field: str | None = None
    field_mapping: dict[str, Any] | None = None


class BitableBaseUrlResolveRequest(BaseModel):
    url: str


class BitableQueryRequest(BaseModel):
    workspace_id: str = "Feishu_demo_Eko"
    query: str
    limit: int = 8


class BitableArchiveRequest(BaseModel):
    workspace_id: str = "Feishu_demo_Eko"
    session_id: str
    artifact: dict[str, Any] = Field(default_factory=dict)


class SyncArtifactUpdateRequest(BaseModel):
    artifact: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    summary: str | None = None
    message: str | None = None


def envelope(data: Any, message: str = "success") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


def chunk_count(content: str) -> int:
    return max(1, (len(content) + 449) // 450)


def file_id_for(source: str, content: str) -> str:
    return hashlib.sha1(f"{source}:{content}".encode("utf-8")).hexdigest()[:16]


def decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore").strip()


def parse_upload(filename: str, content: bytes) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".md", ".markdown", ".txt", ".csv", ".json", ".log"}:
        return suffix.lstrip(".") or "text", decode_text(content)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            with NamedTemporaryFile(suffix=".pdf") as tmp:
                tmp.write(content)
                tmp.flush()
                reader = PdfReader(tmp.name)
                pages = [(page.extract_text() or "").strip() for page in reader.pages]
                text = "\n\n".join(page for page in pages if page).strip()
                return "pdf", text or (reader.metadata.title if reader.metadata else "") or ""
        except Exception as exc:  # pragma: no cover - demo fallback
            raise ValueError(f"PDF parse failed: {exc}") from exc
    if suffix == ".docx":
        try:
            import docx2txt

            with NamedTemporaryFile(suffix=".docx") as tmp:
                tmp.write(content)
                tmp.flush()
                return "docx", (docx2txt.process(tmp.name) or "").strip()
        except Exception as exc:  # pragma: no cover - demo fallback
            raise ValueError(f"DOCX parse failed: {exc}") from exc
    raise ValueError("Unsupported RAG file type. Upload md, txt, csv, json, log, pdf, or docx.")


def create_store_record(
    *,
    filename: str,
    source: str | None,
    content: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if not content.strip():
        raise HTTPException(status_code=400, detail="content must not be empty")
    next_source = source or f"browser-upload://{filename}"
    file_id = file_id_for(next_source, content)
    store[file_id] = {
        "file_id": file_id,
        "filename": filename,
        "source": next_source,
        "content": content,
        "metadata": deepcopy(metadata),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return store[file_id]


def search_terms(query: str) -> list[str]:
    terms = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", query.lower())
    return [term for term in terms if len(term) > 1]


def to_card(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "file_id": record["file_id"],
        "filename": record["filename"],
        "source": record["source"],
        "chunk_count": chunk_count(record["content"]),
        "metadata": deepcopy(record["metadata"]),
        "created_at": record["created_at"],
    }


app = FastAPI(title="Eko RAG Demo API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3002", "http://localhost:3002"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store: dict[str, dict[str, Any]] = {}
users: dict[str, dict[str, Any]] = {}
tokens: dict[str, str] = {}
bitable_sources: dict[str, dict[str, Any]] = {}
sync_sessions: dict[str, dict[str, Any]] = {}


CHAT_WORKFLOW_MESSAGES: list[dict[str, Any]] = [
    {
        "role": "member",
        "sender_name": "刘明（产品）",
        "timestamp": 1717377120,
        "content": "大家早上好，今天同步一下本周的需求排期。本周重点是用户中心 2.0 上线，想确认各端进度。",
    },
    {
        "role": "member",
        "sender_name": "张雯（设计）",
        "timestamp": 1717377360,
        "content": "设计这边已经全部完成了，原型和 UI 稿都上传到 Figma，链接在群公告里，有问题随时找我。",
    },
    {
        "role": "member",
        "sender_name": "李军（后端）",
        "timestamp": 1717377420,
        "content": "后端接口开发完成，今天上午在做单元测试，下午可以提测。接口已经兼容老版本数据，不会有迁移问题。",
    },
    {
        "role": "member",
        "sender_name": "王浩（前端）",
        "timestamp": 1717377480,
        "content": "前端页面开发 80%，剩下个人中心设置页今天能做完，明天可以和后端联调。首页加载慢的 bug 也修好了。",
    },
    {
        "role": "member",
        "sender_name": "刘明（产品）",
        "timestamp": 1717377600,
        "content": "那我们周三下午走内测，周四预发布，周五正式上线。用户反馈登录页验证码太难看，也跟这次版本一起优化。",
    },
    {
        "role": "member",
        "sender_name": "张雯（设计）",
        "timestamp": 1717377960,
        "content": "验证码优化可以，我下午出新版本设计稿。上线前我再走查一遍视觉效果。",
    },
    {
        "role": "member",
        "sender_name": "李军（后端）",
        "timestamp": 1717378200,
        "content": "提醒大家，本周三晚上要做数据迁移，可能会有 15 分钟服务不可用，需要提前通知用户。",
    },
    {
        "role": "member",
        "sender_name": "刘明（产品）",
        "timestamp": 1717378500,
        "content": "好的，我会提前发公告通知用户。今天同步到这里，大家有问题随时在群里说。",
    },
    {
        "role": "assistant",
        "sender_name": "Eko",
        "timestamp": 1717378560,
        "content": "我已根据群聊整理出《用户中心 2.0 上线同步纪要》和一份 6 页 PPT 汇报稿，可在右侧产物区预览、下载并确认。",
    },
]


CHAT_WORKFLOW_DOC = """# 用户中心 2.0 上线同步纪要

## 一、会议背景

本次群聊围绕“用户中心 2.0 本周上线”进行同步，目标是在正式上线前确认设计、前端、后端、测试、发布与用户通知安排，降低跨端协作不确定性。

## 二、当前进展

| 模块 | 负责人 | 当前状态 | 下一步 |
| --- | --- | --- | --- |
| 产品排期 | 刘明 | 已确认周三内测、周四预发布、周五正式上线 | 发布前发用户公告 |
| 设计交付 | 张雯 | 原型和 UI 稿已上传 Figma | 下午补充验证码优化稿，上线前视觉走查 |
| 后端接口 | 李军 | 接口开发完成，单元测试中 | 下午提测，确认老版本数据兼容 |
| 前端页面 | 王浩 | 页面开发约 80%，首页加载慢 bug 已修复 | 完成个人中心设置页，明天联调 |
| 数据迁移 | 李军 | 周三晚执行，预计 15 分钟服务不可用 | 产品提前通知用户 |

## 三、关键结论

- 用户中心 2.0 按当前节奏可以进入本周上线窗口。
- 设计、后端、前端均已明确剩余工作，主要风险集中在联调、数据迁移窗口和上线前公告。
- 登录页验证码视觉优化作为小需求并入本次版本。
- 首页加载慢问题已修复，可纳入本轮回归测试。

## 四、行动项

1. 张雯在今天下午输出验证码优化设计稿。
2. 李军今天下午提交后端接口测试版本，并补齐单元测试结果。
3. 王浩今天完成个人中心设置页，明天与后端联调。
4. 刘明在周三数据迁移前发布用户公告，说明 15 分钟服务不可用窗口。
5. 全员在周三下午参与内测，周四预发布验证，周五正式上线。

## 五、风险与建议

- 数据迁移会带来短暂不可用，建议公告中说明具体时间、影响范围和恢复预期。
- 验证码优化虽然改动较小，但涉及登录入口，建议纳入冒烟测试。
- 周三内测前应确认 Figma 链接、接口文档、前端页面和回归用例都已就绪。

## 六、可发送到飞书群的摘要

用户中心 2.0 本周上线节奏已确认：周三下午内测、周四预发布、周五正式上线。设计稿已完成，验证码优化下午补充；后端接口已完成并进入单测，下午提测；前端完成 80%，今天收尾个人中心设置页，明天联调。周三晚有数据迁移，预计 15 分钟不可用，产品会提前发公告。
"""


CHAT_WORKFLOW_PPT_SLIDES: list[dict[str, Any]] = [
    {
        "slide_number": 1,
        "title": "用户中心 2.0 上线同步",
        "template": "cover",
        "right_items": ["群聊纪要生成", "周三内测 / 周四预发布 / 周五上线", "Eko 本地演示产物"],
    },
    {
        "slide_number": 2,
        "title": "本周上线目标",
        "template": "agenda",
        "right_items": ["确认用户中心 2.0 各端进展", "同步验证码视觉优化并入版本", "提前暴露数据迁移与联调风险"],
    },
    {
        "slide_number": 3,
        "title": "各端进度",
        "template": "status",
        "right_items": ["设计：原型和 UI 稿已上传 Figma", "后端：接口完成，单测中，下午提测", "前端：页面完成 80%，设置页今日收尾"],
    },
    {
        "slide_number": 4,
        "title": "发布节奏",
        "template": "timeline",
        "right_items": ["周三下午：内测", "周三晚上：数据迁移，约 15 分钟不可用", "周四：预发布", "周五：正式上线"],
    },
    {
        "slide_number": 5,
        "title": "风险与缓解",
        "template": "risk",
        "right_items": ["迁移窗口需提前公告", "登录页验证码优化需冒烟验证", "联调前确认接口兼容老数据", "上线前补充视觉走查"],
    },
    {
        "slide_number": 6,
        "title": "行动项",
        "template": "next",
        "right_items": ["张雯：下午交付验证码优化稿", "李军：下午提测并同步单测结果", "王浩：完成设置页并准备联调", "刘明：发布迁移公告并组织内测"],
    },
]

DEMO_BITABLE_BASES = [
    {"id": "bb_demo_project", "name": "Eko 演示项目多维表格", "source": "user_oauth", "app_token": "bascn_demo_project"},
    {"id": "bb_demo_customer", "name": "客户活动记录表", "source": "user_oauth", "app_token": "bascn_demo_customer"},
]

DEMO_BITABLE_TABLES = {
    "bb_demo_project": [
        {"id": "tbl_project_plan", "name": "项目排期"},
        {"id": "tbl_launch_tasks", "name": "上线任务"},
    ],
    "bb_demo_customer": [
        {"id": "tbl_customer_events", "name": "客户活动"},
    ],
}

DEMO_BITABLE_VIEWS = {
    "tbl_project_plan": [{"id": "vew_all", "name": "全部记录", "type": "grid"}, {"id": "vew_active", "name": "进行中", "type": "grid"}],
    "tbl_launch_tasks": [{"id": "vew_all", "name": "全部任务", "type": "grid"}],
    "tbl_customer_events": [{"id": "vew_all", "name": "全部活动", "type": "grid"}],
}

DEMO_BITABLE_FIELDS = {
    "tbl_project_plan": [
        {"id": "fld_title", "name": "任务名称", "type": "text"},
        {"id": "fld_summary", "name": "任务描述", "type": "text"},
        {"id": "fld_owner", "name": "负责人", "type": "user"},
        {"id": "fld_status", "name": "状态", "type": "single_select"},
        {"id": "fld_date", "name": "截止日期", "type": "date"},
        {"id": "fld_url", "name": "链接", "type": "url"},
    ],
    "tbl_launch_tasks": [
        {"id": "fld_title", "name": "任务名称", "type": "text"},
        {"id": "fld_summary", "name": "描述", "type": "text"},
        {"id": "fld_owner", "name": "负责人", "type": "user"},
        {"id": "fld_status", "name": "状态", "type": "single_select"},
    ],
    "tbl_customer_events": [
        {"id": "fld_title", "name": "活动名称", "type": "text"},
        {"id": "fld_summary", "name": "客户反馈", "type": "text"},
        {"id": "fld_owner", "name": "负责人", "type": "user"},
        {"id": "fld_status", "name": "状态", "type": "single_select"},
        {"id": "fld_date", "name": "活动日期", "type": "date"},
    ],
}

DEMO_BITABLE_RECORDS = {
    "tbl_project_plan": [
        {"record_id": "rec_project_1", "fields": {"任务名称": "RAG 资料预览与编辑", "任务描述": "完成知识库导入后预览、编辑和重新索引流程", "负责人": "LJY", "状态": "进行中", "截止日期": "2026-05-15", "链接": "https://example.feishu.cn/base/demo/rec_project_1"}},
        {"record_id": "rec_project_2", "fields": {"任务名称": "Bitable 本地演示链路", "任务描述": "无需真实飞书授权即可测试多维表格数据源", "负责人": "Eko", "状态": "待验收", "截止日期": "2026-05-18", "链接": "https://example.feishu.cn/base/demo/rec_project_2"}},
        {"record_id": "rec_project_3", "fields": {"任务名称": "Agent 结合项目排期", "任务描述": "Agent 可读取负责人、状态和截止日期作为结构化上下文", "负责人": "Product", "状态": "已完成", "截止日期": "2026-05-10", "链接": "https://example.feishu.cn/base/demo/rec_project_3"}},
    ],
    "tbl_launch_tasks": [
        {"record_id": "rec_launch_1", "fields": {"任务名称": "灰度发布检查", "描述": "检查登录、知识库、Bitable 三条链路", "负责人": "QA", "状态": "进行中"}},
        {"record_id": "rec_launch_2", "fields": {"任务名称": "演示数据冻结", "描述": "保留长期演示样例，避免自动删除", "负责人": "Ops", "状态": "未开始"}},
    ],
    "tbl_customer_events": [
        {"record_id": "rec_customer_1", "fields": {"活动名称": "飞书知识库演示", "客户反馈": "希望绑定后能自动发现多维表格并测试查询", "负责人": "Sales", "状态": "跟进中", "活动日期": "2026-05-20"}},
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_app_token(token: str | None) -> str | None:
    if not token:
        return None
    if len(token) <= 8:
        return f"{token[:2]}***"
    return f"{token[:6]}***{token[-4:]}"


def demo_base_by_id(base_id: str | None) -> dict[str, Any] | None:
    if not base_id:
        return None
    return next((base for base in DEMO_BITABLE_BASES if base["id"] == base_id or base["app_token"] == base_id), None)


def base_for_table(table_id: str | None) -> dict[str, Any] | None:
    if not table_id:
        return None
    for base in DEMO_BITABLE_BASES:
        if any(table["id"] == table_id for table in DEMO_BITABLE_TABLES.get(base["id"], [])):
            return base
    return None


def demo_table_by_id(table_id: str | None) -> dict[str, Any] | None:
    if not table_id:
        return None
    for tables in DEMO_BITABLE_TABLES.values():
        match = next((table for table in tables if table["id"] == table_id), None)
        if match:
            return match
    return None


def source_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    table_id = source["table_id"]
    table = demo_table_by_id(table_id) or {"id": table_id, "name": table_id}
    return {
        "base": demo_base_by_id(source.get("base_id")) or base_for_table(table_id),
        "table": table,
        "views": deepcopy(DEMO_BITABLE_VIEWS.get(table_id, [])),
        "fields": deepcopy(DEMO_BITABLE_FIELDS.get(table_id, [])),
        "record_count": len(DEMO_BITABLE_RECORDS.get(table_id, [])),
    }


def source_from_payload(payload: BitableSourcePayload) -> dict[str, Any]:
    table_id = payload.table_id.strip()
    if not table_id:
        raise HTTPException(status_code=400, detail="table_id must not be empty")
    base = demo_base_by_id(payload.base_id) or base_for_table(table_id)
    app_token = payload.app_token or (base["app_token"] if base else None)
    now = now_iso()
    source_id = f"bt_{hashlib.sha1(f'{payload.workspace_id}:{payload.name}:{table_id}:{now}'.encode('utf-8')).hexdigest()[:12]}"
    source = {
        "id": source_id,
        "workspace_id": payload.workspace_id,
        "name": payload.name.strip() or table_id,
        "base_id": base["id"] if base else payload.base_id,
        "app_token_masked": mask_app_token(app_token),
        "table_id": table_id,
        "view_id": payload.view_id,
        "enabled": True,
        "purpose": payload.purpose,
        "title_field": payload.title_field,
        "summary_field": payload.summary_field,
        "url_field": payload.url_field,
        "status_field": payload.status_field,
        "type_field": payload.type_field,
        "owner_field": payload.owner_field,
        "date_field": payload.date_field,
        "field_mapping": deepcopy(payload.field_mapping),
        "last_schema_snapshot": {},
        "last_check_status": None,
        "last_check_error": None,
        "created_at": now,
        "updated_at": now,
    }
    source["last_schema_snapshot"] = source_snapshot(source)
    return source


def update_source_from_patch(source: dict[str, Any], payload: BitableSourcePatch) -> dict[str, Any]:
    update = payload.model_dump(exclude_unset=True)
    for key, value in update.items():
        if key == "app_token":
            source["app_token_masked"] = mask_app_token(value)
        elif key in source:
            source[key] = deepcopy(value)
    source["updated_at"] = now_iso()
    return source


def source_response(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in source.items()
        if key != "base_id"
    }


def field_value(fields: dict[str, Any], configured: str | None, fallback_index: int = 0) -> Any:
    if configured and configured in fields:
        return fields[configured]
    values = list(fields.values())
    if values and fallback_index < 0:
        return values[fallback_index]
    if values and 0 <= fallback_index < len(values):
        return values[fallback_index]
    return ""


def bitable_record_context(source: dict[str, Any], record: dict[str, Any], query: str) -> dict[str, Any]:
    fields = deepcopy(record.get("fields", {}))
    title = str(field_value(fields, source.get("title_field"), 0) or record["record_id"])
    summary = str(field_value(fields, source.get("summary_field"), 1) or "")
    record_url = str(field_value(fields, source.get("url_field"), -1) or "")
    content_parts = [title, summary]
    for key, value in fields.items():
        content_parts.append(f"{key}: {value}")
    content = "\n".join(part for part in content_parts if part)
    terms = search_terms(query)
    haystack = content.lower()
    matches = [term for term in terms if term in haystack]
    exact = bool(query.strip() and query.strip().lower() in haystack)
    score = 1.0 if exact else (0.55 + min(0.4, len(matches) / max(len(terms), 1) * 0.4) if matches else 0.3)
    table = demo_table_by_id(source["table_id"])
    return {
        "source_id": source["id"],
        "source_name": source["name"],
        "source_type": "bitable",
        "table_id": source["table_id"],
        "table_name": table["name"] if table else source["table_id"],
        "record_id": record["record_id"],
        "title": title,
        "summary": summary,
        "content": content,
        "fields": fields,
        "score": score,
        "record_url": record_url or None,
    }


def artifact_return_source(session_id: str, kind: str) -> str:
    normalized_kind = kind.strip().lower() or "artifact"
    return f"demo://artifact-return/{session_id}/{normalized_kind}"


def artifact_to_rag_content(session_id: str, artifact: dict[str, Any]) -> str:
    kind = str(artifact.get("kind") or "artifact").lower()
    title = str(artifact.get("title") or ("AI PPT" if kind == "ppt" else "Eko 文档"))
    summary = str(artifact.get("result_summary") or artifact.get("current_step") or "工具端已确认当前产物。")
    lines = [
        f"# {title}",
        "",
        "这是一条本地演示回流资料，用于验证生成产物确认后进入知识库索引。",
        "",
        f"- 会话 ID：{session_id}",
        f"- 产物类型：{kind}",
        f"- 确认状态：{artifact.get('status') or 'confirmed'}",
        f"- 摘要：{summary}",
    ]
    if kind == "ppt":
        if artifact.get("download_url"):
            lines.append(f"- PPT 下载链接：{artifact['download_url']}")
        if artifact.get("preview_url"):
            lines.append(f"- PPT 预览链接：{artifact['preview_url']}")
        if artifact.get("sharing_url"):
            lines.append(f"- 分享链接：{artifact['sharing_url']}")
        lines.extend(["", "## PPT 说明", summary])
    else:
        if artifact.get("sharing_url"):
            lines.append(f"- 分享链接：{artifact['sharing_url']}")
        content = str(artifact.get("content") or "").strip()
        lines.extend(["", "## 正文内容", content or summary])
    return "\n".join(lines).strip()


def upsert_artifact_return_to_rag(session_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    kind = str(artifact.get("kind") or "artifact").lower()
    source = artifact_return_source(session_id, kind)
    title = str(artifact.get("title") or ("AI PPT 回流资料" if kind == "ppt" else "文档回流资料"))
    for existing_file_id, existing_record in list(store.items()):
        if existing_record.get("source") == source:
            store.pop(existing_file_id, None)
    return create_store_record(
        filename=f"{title} - 知识库回流.md",
        source=source,
        content=artifact_to_rag_content(session_id, artifact),
        metadata={
            "category": "artifact_return",
            "session_id": session_id,
            "artifact_kind": kind,
            "returned_from": "sync_confirm",
            "demo": True,
            "note": "本地演示：确认产物后自动回流到 RAG 知识库。",
        },
    )


def records_to_context_text(query: str, records: list[dict[str, Any]]) -> str:
    lines = ["## Bitable 生成依据", f"查询：{query.strip() or '全部记录'}"]
    if records:
        first = records[0]
        lines.insert(1, f"数据源：{first.get('source_name') or '本地模拟数据源'}")
        lines.insert(2, f"数据表：{first.get('table_name') or first.get('table_id') or '模拟多维表格'}")
    lines.append("")
    for index, record in enumerate(records, start=1):
        lines.append(f"### 记录 {index}：{record.get('title') or record.get('record_id')}")
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        for key, value in fields.items():
            lines.append(f"{key}：{value}")
        if record.get("summary"):
            lines.append(f"摘要：{record['summary']}")
        if record.get("record_url"):
            lines.append(f"链接：{record['record_url']}")
        lines.append("")
    return "\n".join(lines).strip()


def bitable_source_snapshot(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"sources": [], "fields": []}
    source_ids: list[str] = []
    sources: list[dict[str, Any]] = []
    field_names: list[str] = []
    for record in records:
        source_id = str(record.get("source_id") or "")
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)
            source = bitable_sources.get(source_id)
            sources.append(source_response(source) if source else {"id": source_id, "name": record.get("source_name")})
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        for key in fields:
            if key not in field_names:
                field_names.append(key)
    return {"sources": sources, "fields": field_names}


def mock_bitable_archive_results(session_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for source in bitable_sources.values():
        if source.get("workspace_id") != "Feishu_demo_Eko" or not source.get("enabled"):
            continue
        if source.get("purpose") not in {"archive", "both"}:
            continue
        archive_key = f"{session_id}:{source['id']}"
        record_id = f"mock_archive_{hashlib.sha1(archive_key.encode('utf-8')).hexdigest()[:10]}"
        results.append(
            {
                "source_id": source["id"],
                "source_name": source["name"],
                "status": "ok",
                "record_id": record_id,
                "record_url": f"https://example.feishu.cn/base/mock/{source['table_id']}/{record_id}",
                "message": "已回流到模拟多维表格，真实飞书未被写入。",
            }
        )
    return results


def demo_ppt_preview(job_id: str) -> dict[str, Any]:
    if job_id != "demo-ppt-complete-local":
        raise HTTPException(status_code=404, detail="PPT preview job not found")
    return {
        "job_id": job_id,
        "title": "用户中心 2.0 上线同步汇报",
        "subtitle": "根据飞书群聊自动生成的本地演示 PPT",
        "page_count": len(CHAT_WORKFLOW_PPT_SLIDES),
        "status": "completed",
        "progress": 100,
        "download_url": "https://example.com/downloads/user-center-2-sync-demo.pptx",
        "slides": deepcopy(CHAT_WORKFLOW_PPT_SLIDES),
    }


def demo_slide_svg(slide: dict[str, Any]) -> str:
    title = str(slide.get("title") or "用户中心 2.0")
    items = [str(item) for item in slide.get("right_items") or []]
    colors = [
        ("#0f172a", "#2563eb", "#dbeafe"),
        ("#1f2937", "#059669", "#dcfce7"),
        ("#172554", "#ea580c", "#ffedd5"),
        ("#312e81", "#7c3aed", "#ede9fe"),
        ("#3f1d2f", "#e11d48", "#ffe4e6"),
        ("#052e16", "#16a34a", "#dcfce7"),
    ]
    index = max(0, int(slide.get("slide_number") or 1) - 1)
    bg, accent, soft = colors[index % len(colors)]
    bullets = "\n".join(
        f'<text x="132" y="{342 + offset * 62}" fill="#f8fafc" font-size="34" font-family="Microsoft YaHei, Arial">• {item}</text>'
        for offset, item in enumerate(items[:4])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{bg}"/>
      <stop offset="1" stop-color="#020617"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="22" stdDeviation="22" flood-color="#020617" flood-opacity="0.28"/>
    </filter>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <circle cx="1320" cy="120" r="260" fill="{accent}" opacity="0.22"/>
  <circle cx="1450" cy="760" r="360" fill="{soft}" opacity="0.12"/>
  <rect x="88" y="76" width="1424" height="748" rx="44" fill="#ffffff" opacity="0.08" filter="url(#shadow)"/>
  <text x="128" y="152" fill="{soft}" font-size="28" font-weight="700" font-family="Microsoft YaHei, Arial">Eko 生成产物 · 第 {index + 1} 页</text>
  <text x="128" y="258" fill="#ffffff" font-size="70" font-weight="800" font-family="Microsoft YaHei, Arial">{title}</text>
  <rect x="128" y="292" width="172" height="10" rx="5" fill="{accent}"/>
  {bullets}
  <text x="128" y="770" fill="#cbd5e1" font-size="26" font-family="Microsoft YaHei, Arial">来源：本地 mock 飞书群聊 · 用户中心 2.0 上线同步</text>
  <text x="1370" y="770" fill="#e2e8f0" font-size="54" font-weight="800" font-family="Arial">{index + 1:02d}</text>
</svg>"""


def ensure_seed_bitable_source() -> None:
    if any(source.get("workspace_id") == "Feishu_demo_Eko" for source in bitable_sources.values()):
        return
    payload = BitableSourcePayload(
        workspace_id="Feishu_demo_Eko",
        name="Eko 演示项目多维表格 / 项目排期",
        base_id="bb_demo_project",
        table_id="tbl_project_plan",
        view_id="vew_active",
        purpose="both",
        title_field=DEMO_BITABLE_FIELDS["tbl_project_plan"][0]["name"],
        summary_field=DEMO_BITABLE_FIELDS["tbl_project_plan"][1]["name"],
        owner_field=DEMO_BITABLE_FIELDS["tbl_project_plan"][2]["name"],
        status_field=DEMO_BITABLE_FIELDS["tbl_project_plan"][3]["name"],
        date_field=DEMO_BITABLE_FIELDS["tbl_project_plan"][4]["name"],
        url_field=DEMO_BITABLE_FIELDS["tbl_project_plan"][5]["name"],
        field_mapping={"demo": True},
    )
    source = source_from_payload(payload)
    source["id"] = "bt_demo_project_plan"
    source["last_check_status"] = "ok"
    bitable_sources[source["id"]] = source


def ensure_demo_session(session_id: str) -> dict[str, Any]:
    now = now_iso()
    session = sync_sessions.get(session_id)
    if session is not None:
        return session
    if session_id == "demo-doc-workflow":
        artifact = {
            "kind": "docx",
            "intent": "docx",
            "title": "用户中心 2.0 上线同步纪要",
            "content": CHAT_WORKFLOW_DOC,
            "status": "completed",
            "current_step": "文档已生成，等待确认",
            "sharing_url": "https://example.feishu.cn/docx/user-center-2-demo-minutes",
            "result_summary": "已根据群聊生成用户中心 2.0 上线同步纪要，可预览、编辑、保存草稿并确认回流知识库。",
        }
        session = {
            "session_id": session_id,
            "source": "app",
            "title": "用户中心 2.0 上线同步纪要",
            "summary": "根据群聊生成的会议纪要文档，包含进度、排期、风险和行动项。",
            "status": "completed",
            "user_id": default_user()["user_id"],
            "opened_at": now,
            "updated_at": now,
            "chat_id": None,
            "message_id": None,
            "context_size": len(CHAT_WORKFLOW_MESSAGES),
            "instruction": "请根据群聊内容生成一份用户中心 2.0 上线同步纪要，包含当前进展、上线节奏、风险和行动项。",
            "intent": "docx",
            "artifact": artifact,
            "context_messages": deepcopy(CHAT_WORKFLOW_MESSAGES[:-1]),
            "selected_context_messages": deepcopy(CHAT_WORKFLOW_MESSAGES[:-1]),
            "messages": deepcopy(CHAT_WORKFLOW_MESSAGES),
        }
        sync_sessions[session_id] = session
        return session
    if session_id == "demo-ppt-workflow":
        artifact = {
            "kind": "ppt",
            "intent": "ppt",
            "title": "用户中心 2.0 上线同步汇报",
            "job_id": "demo-ppt-complete-local",
            "status": "completed",
            "progress": 100,
            "current_step": "completed",
            "download_url": "https://example.com/downloads/user-center-2-sync-demo.pptx",
            "preview_url": None,
            "sharing_url": "https://example.feishu.cn/docx/user-center-2-demo-ppt",
            "result_summary": "已根据群聊生成 6 页用户中心 2.0 上线同步 PPT，可预览、下载并确认回流知识库。",
        }
        session = {
            "session_id": session_id,
            "source": "app",
            "title": "用户中心 2.0 上线同步汇报",
            "summary": "根据群聊生成的 6 页 PPT 汇报稿，覆盖目标、进度、排期、风险和行动项。",
            "status": "completed",
            "user_id": default_user()["user_id"],
            "opened_at": now,
            "updated_at": now,
            "chat_id": None,
            "message_id": None,
            "context_size": len(CHAT_WORKFLOW_MESSAGES),
            "instruction": "请根据群聊内容生成一份用户中心 2.0 上线同步 PPT，适合发到飞书群里快速缓解团队焦虑。",
            "intent": "ppt",
            "artifact": artifact,
            "context_messages": deepcopy(CHAT_WORKFLOW_MESSAGES[:-1]),
            "selected_context_messages": deepcopy(CHAT_WORKFLOW_MESSAGES[:-1]),
            "messages": deepcopy(CHAT_WORKFLOW_MESSAGES),
        }
        sync_sessions[session_id] = session
        return session
    session = {
        "session_id": session_id,
        "source": "app",
        "title": "Eko 产物编辑演示",
        "summary": "本地演示会话，可用于验证产物预览、编辑、保存草稿和确认。",
        "status": "completed",
        "user_id": default_user()["user_id"],
        "opened_at": now,
        "updated_at": now,
        "chat_id": None,
        "message_id": None,
        "context_size": 0,
        "instruction": "请生成一份用于演示的文档产物。",
        "intent": "docx",
        "artifact": {
            "kind": "docx",
            "intent": "docx",
            "title": "Eko 产物编辑演示",
            "content": "# Eko 产物编辑演示\n\n这是一份本地演示文档，用于验证工具端产物编辑体验。\n\n## 可验证能力\n\n- 预览生成后的 Markdown 文档。\n- 在工具端编辑正文。\n- 保存草稿到当前会话 artifact。\n- 确认产物并保持飞书链接入口不丢失。\n",
            "status": "completed",
            "current_step": "文档已生成",
            "sharing_url": "https://example.feishu.cn/docx/mock-demo-doc",
            "result_summary": "演示文档已准备。",
        },
        "context_messages": [],
        "selected_context_messages": [],
        "messages": [
            {"role": "user", "content": "请生成一份演示文档"},
            {"role": "assistant", "content": "已生成文档产物，可以在右侧预览并编辑。"},
        ],
    }
    sync_sessions[session_id] = session
    return session


def default_user(email: str = "demo@eko.local", display_name: str = "Eko Demo User") -> dict[str, Any]:
    normalized = email.strip().lower()
    return {
        "user_id": hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16],
        "display_name": display_name,
        "name_en": "Eko Demo User",
        "feishu_user_id": f"mock-feishu-{hashlib.sha1(normalized.encode('utf-8')).hexdigest()[:8]}",
        "email": normalized,
        "avatar_url": None,
        "feishu_bound": True,
        "union_id": "mock-union-demo",
        "phone": "",
        "phone_ext": "",
        "location": "Shanghai",
        "time_zone": "Asia/Shanghai",
        "employee_id": "EKO-DEMO-001",
        "job_title": "Demo Tester",
        "department": "Product Demo",
        "team": "RAG Showcase",
        "reports_to": "",
        "joined_at": "2026-05-11",
        "bio": "本地演示账号，用于测试前端登录、资料编辑和 RAG 知识库流程。",
        "languages": ["zh-CN"],
    }


def issue_token(user: dict[str, Any]) -> dict[str, Any]:
    token = f"demo-token-{secrets.token_urlsafe(18)}"
    tokens[token] = user["email"]
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 15 * 24 * 60 * 60,
        "user": deepcopy(user),
    }


def user_from_authorization(authorization: str | None) -> dict[str, Any]:
    token = ""
    if authorization:
        parts = authorization.split()
        token = parts[-1] if parts else ""
    email = tokens.get(token) or "demo@eko.local"
    return users.setdefault(email, default_user(email))


def seed_demo() -> None:
    source = "demo://rag-edit-showcase/permanent"
    file_id = file_id_for(source, DEMO_CONTENT)
    store[file_id] = {
        "file_id": file_id,
        "filename": "Eko RAG 编辑演示资料.md",
        "source": source,
        "content": DEMO_CONTENT,
        "metadata": {
            "workspace_id": "Feishu_demo_Eko",
            "note": "长期演示样例：用于验证 RAG 资料预览、编辑和重新索引能力。",
            "demo": True,
            "category": "rag_edit_showcase",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users["demo@eko.local"] = default_user()
    ensure_seed_bitable_source()
    ensure_demo_session("demo-doc-workflow")
    ensure_demo_session("demo-ppt-workflow")


seed_demo()


@app.get("/api/v1/bitable/discovery/status")
async def bitable_discovery_status() -> dict[str, Any]:
    return envelope(
        {
            "bound": True,
            "needs_reauth": False,
            "identity_label": "飞书模拟用户",
            "mode": "user_oauth",
            "message": "本地模拟飞书授权已开启，可直接测试 Bitable 发现、配置和查询流程。",
        }
    )


@app.get("/api/v1/bitable/discovery/bases")
async def list_bitable_bases() -> dict[str, Any]:
    return envelope(
        [
            {
                "id": base["id"],
                "name": base["name"],
                "source": base["source"],
                "app_token_masked": mask_app_token(base["app_token"]),
            }
            for base in DEMO_BITABLE_BASES
        ]
    )


@app.post("/api/v1/bitable/discovery/resolve-url")
async def resolve_bitable_url(payload: BitableBaseUrlResolveRequest) -> dict[str, Any]:
    text = payload.url.strip()
    base = next((item for item in DEMO_BITABLE_BASES if item["app_token"] in text or item["id"] in text), DEMO_BITABLE_BASES[0])
    table_match = re.search(r"(tbl_[A-Za-z0-9_]+)", text)
    view_match = re.search(r"(vew_[A-Za-z0-9_]+)", text)
    tables = DEMO_BITABLE_TABLES.get(base["id"], [])
    table_id = table_match.group(1) if table_match and any(table["id"] == table_match.group(1) for table in tables) else tables[0]["id"]
    views = DEMO_BITABLE_VIEWS.get(table_id, [])
    view_id = view_match.group(1) if view_match and any(view["id"] == view_match.group(1) for view in views) else (views[0]["id"] if views else None)
    return envelope(
        {
            "base": {
                "id": base["id"],
                "name": base["name"],
                "source": base["source"],
                "app_token_masked": mask_app_token(base["app_token"]),
            },
            "table_id": table_id,
            "view_id": view_id,
        }
    )


@app.get("/api/v1/bitable/discovery/tables")
async def list_bitable_tables(base_id: str) -> dict[str, Any]:
    if base_id not in DEMO_BITABLE_TABLES:
        raise HTTPException(status_code=404, detail="Bitable base not found in local demo data")
    return envelope(deepcopy(DEMO_BITABLE_TABLES[base_id]))


@app.get("/api/v1/bitable/discovery/views")
async def list_bitable_views(base_id: str, table_id: str) -> dict[str, Any]:
    if base_id not in DEMO_BITABLE_TABLES:
        raise HTTPException(status_code=404, detail="Bitable base not found in local demo data")
    return envelope(deepcopy(DEMO_BITABLE_VIEWS.get(table_id, [])))


@app.get("/api/v1/bitable/discovery/fields")
async def list_bitable_fields(base_id: str, table_id: str) -> dict[str, Any]:
    if base_id not in DEMO_BITABLE_TABLES:
        raise HTTPException(status_code=404, detail="Bitable base not found in local demo data")
    return envelope(deepcopy(DEMO_BITABLE_FIELDS.get(table_id, [])))


@app.get("/api/v1/bitable/sources")
async def list_bitable_sources(workspace_id: str = "Feishu_demo_Eko") -> dict[str, Any]:
    sources = [
        source_response(source)
        for source in bitable_sources.values()
        if source.get("workspace_id") == workspace_id
    ]
    sources.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return envelope(sources)


@app.post("/api/v1/bitable/sources")
async def create_bitable_source(payload: BitableSourcePayload) -> dict[str, Any]:
    source = source_from_payload(payload)
    bitable_sources[source["id"]] = source
    return envelope(source_response(source))


@app.patch("/api/v1/bitable/sources/{source_id}")
async def update_bitable_source(source_id: str, payload: BitableSourcePatch) -> dict[str, Any]:
    source = bitable_sources.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Bitable source not found")
    update_source_from_patch(source, payload)
    return envelope(source_response(source))


@app.delete("/api/v1/bitable/sources/{source_id}")
async def delete_bitable_source(source_id: str) -> dict[str, Any]:
    if bitable_sources.pop(source_id, None) is None:
        raise HTTPException(status_code=404, detail="Bitable source not found")
    return envelope(None)


@app.post("/api/v1/bitable/sources/{source_id}/inspect")
async def inspect_bitable_source(source_id: str) -> dict[str, Any]:
    source = bitable_sources.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Bitable source not found")
    snapshot = source_snapshot(source)
    source["last_schema_snapshot"] = snapshot
    source["last_check_status"] = "ok"
    source["last_check_error"] = None
    source["updated_at"] = now_iso()
    return envelope(
        {
            "source": source_response(source),
            "table": deepcopy(snapshot.get("table") or {}),
            "fields": deepcopy(snapshot.get("fields") or []),
            "views": deepcopy(snapshot.get("views") or []),
            "raw": snapshot,
        }
    )


@app.post("/api/v1/bitable/query")
async def query_bitable(payload: BitableQueryRequest) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    terms = search_terms(payload.query)
    for source in bitable_sources.values():
        if source.get("workspace_id") != payload.workspace_id or not source.get("enabled"):
            continue
        if source.get("purpose") not in {"context", "both"}:
            continue
        table_records = DEMO_BITABLE_RECORDS.get(source["table_id"], [])
        if not table_records:
            failures.append({"source_id": source["id"], "message": "本地演示数据没有该表记录"})
            continue
        for record in table_records:
            context = bitable_record_context(source, record, payload.query)
            haystack = context["content"].lower()
            if not terms or any(term in haystack for term in terms) or payload.query.strip().lower() in haystack:
                records.append(context)
    records.sort(key=lambda item: item["score"], reverse=True)
    limited_records = records[: max(1, payload.limit)]
    return envelope(
        {
            "records": limited_records,
            "failures": failures,
            "context_text": records_to_context_text(payload.query, limited_records),
            "source_snapshot": bitable_source_snapshot(limited_records),
        }
    )


@app.post("/api/v1/bitable/archive")
async def archive_bitable(payload: BitableArchiveRequest) -> dict[str, Any]:
    results = []
    for source in bitable_sources.values():
        if source.get("workspace_id") != payload.workspace_id or not source.get("enabled"):
            continue
        if source.get("purpose") not in {"archive", "both"}:
            continue
        archive_key = f"{payload.session_id}:{source['id']}"
        record_id = f"mock_archive_{hashlib.sha1(archive_key.encode('utf-8')).hexdigest()[:10]}"
        results.append(
            {
                "source_id": source["id"],
                "source_name": source["name"],
                "status": "ok",
                "record_id": record_id,
                "record_url": f"https://example.feishu.cn/base/mock/{source['table_id']}/{record_id}",
                "message": "本地模拟归档成功，真实飞书未被写入。",
            }
        )
    for item in results:
        item["message"] = "已回流到模拟多维表格，真实飞书未被写入。"
    return envelope({"results": results, "artifact": payload.artifact})


@app.get("/api/v1/bitable/schema")
async def get_bitable_schema(workspace_id: str = "Feishu_demo_Eko") -> dict[str, Any]:
    return envelope(
        {
            "workspace_id": workspace_id,
            "sources": [source_response(source) for source in bitable_sources.values() if source.get("workspace_id") == workspace_id],
            "demo_bases": deepcopy(DEMO_BITABLE_BASES),
        }
    )


@app.get("/api/v1/ppt/preview/{job_id}")
async def get_ppt_preview(job_id: str) -> dict[str, Any]:
    return envelope(demo_ppt_preview(job_id))


@app.get("/api/v1/ppt/preview/{job_id}/slides/{slide_number}")
async def get_ppt_preview_slide(job_id: str, slide_number: int) -> Response:
    preview = demo_ppt_preview(job_id)
    slide = next((item for item in preview["slides"] if item.get("slide_number") == slide_number), None)
    if slide is None:
        raise HTTPException(status_code=404, detail="PPT slide not found")
    return Response(content=demo_slide_svg(slide), media_type="image/svg+xml")


@app.get("/api/v1/rag/files")
async def list_files() -> dict[str, Any]:
    return envelope([to_card(record) for record in store.values()])


@app.get("/api/v1/sync/sessions/{session_id}")
async def get_sync_session(session_id: str) -> dict[str, Any]:
    return envelope(ensure_demo_session(session_id))


@app.patch("/api/v1/sync/sessions/{session_id}/artifact")
async def update_sync_artifact(session_id: str, payload: SyncArtifactUpdateRequest) -> dict[str, Any]:
    session = ensure_demo_session(session_id)
    artifact = dict(session.get("artifact") or {})
    artifact.update(deepcopy(payload.artifact))
    if str(artifact.get("status") or "").lower() == "confirmed":
        rag_record = upsert_artifact_return_to_rag(session_id, artifact)
        artifact["rag_return_file_id"] = rag_record["file_id"]
        artifact["rag_return_source"] = rag_record["source"]
        artifact["rag_return_message"] = "已确认，并已加入知识库演示索引"
        artifact["bitable_archive_results"] = mock_bitable_archive_results(session_id)
    session["artifact"] = artifact
    session["status"] = payload.status or session["status"]
    session["summary"] = payload.summary or payload.message or session["summary"]
    session["updated_at"] = now_iso()
    return envelope(session)


@app.post("/api/v1/auth/register")
async def register(payload: AuthRegisterRequest) -> dict[str, Any]:
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="invalid email")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 characters")
    user = users.setdefault(email, default_user(email=email, display_name=payload.display_name.strip() or email))
    user["display_name"] = payload.display_name.strip() or user["display_name"]
    return envelope(issue_token(user))


@app.post("/api/v1/auth/login")
async def login(payload: AuthLoginRequest) -> dict[str, Any]:
    email = payload.email.strip().lower() or "demo@eko.local"
    if not payload.password.strip():
        raise HTTPException(status_code=400, detail="password must not be empty")
    user = users.setdefault(email, default_user(email=email, display_name=email.split("@")[0] or "Eko Demo User"))
    return envelope(issue_token(user))


@app.get("/api/v1/auth/me")
async def me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return envelope(user_from_authorization(authorization))


@app.patch("/api/v1/auth/me")
async def update_me(payload: AuthUserUpdateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = user_from_authorization(authorization)
    update = payload.model_dump(exclude_unset=True)
    for key, value in update.items():
        if value is not None:
            user[key] = value
    if "email" in update and isinstance(update["email"], str) and update["email"].strip():
        normalized = update["email"].strip().lower()
        users.pop(user["email"], None)
        user["email"] = normalized
        users[normalized] = user
    return envelope(user)


@app.patch("/api/v1/auth/me/password")
async def update_password(payload: AuthPasswordUpdateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="new password must be at least 8 characters")
    return envelope(user_from_authorization(authorization))


@app.get("/api/v1/auth/feishu/login-url")
async def feishu_login_url(redirect_uri: str | None = None) -> dict[str, Any]:
    state = f"mock-state-{secrets.token_urlsafe(8)}"
    target = redirect_uri or "http://127.0.0.1:3002/login/feishu/callback"
    authorize_url = f"{target}{'&' if '?' in target else '?'}{urlencode({'code': 'mock-feishu-code', 'state': state})}"
    return envelope({"authorize_url": authorize_url, "state": state, "expires_in": 600})


@app.post("/api/v1/auth/feishu/login")
async def feishu_login(payload: FeishuLoginRequest) -> dict[str, Any]:
    user = users.setdefault("feishu.demo@eko.local", default_user("feishu.demo@eko.local", "飞书模拟用户"))
    user["feishu_bound"] = True
    user["feishu_user_id"] = "mock-feishu-open-id"
    user["union_id"] = "mock-feishu-union-id"
    return envelope(issue_token(user))


@app.post("/api/v1/auth/feishu/bind")
async def feishu_bind(payload: FeishuLoginRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = user_from_authorization(authorization)
    user["feishu_bound"] = True
    user["feishu_user_id"] = "mock-feishu-open-id"
    user["union_id"] = "mock-feishu-union-id"
    return envelope(user)


@app.post("/api/v1/rag/files")
async def create_file(payload: RagFileCreateRequest) -> dict[str, Any]:
    record = create_store_record(
        filename=payload.filename,
        source=payload.source,
        content=payload.content,
        metadata=payload.metadata,
    )
    return envelope(to_card(record))


@app.post("/api/v1/rag/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    source: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
) -> dict[str, Any]:
    content = await file.read()
    filename = file.filename or "upload.txt"
    try:
        file_type, text = parse_upload(filename, content)
        parsed_metadata = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError as exc:
        parsed_metadata = {"raw_metadata": metadata, "metadata_parse_error": str(exc)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not isinstance(parsed_metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")
    record = create_store_record(
        filename=filename,
        source=source,
        content=text,
        metadata={
            **parsed_metadata,
            "file_type": file_type,
            "upload_filename": filename,
            "content_length": len(text),
        },
    )
    return envelope(to_card(record))


@app.get("/api/v1/rag/files/{file_id}/content")
async def get_content(file_id: str) -> dict[str, Any]:
    record = store.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="RAG file not found")
    return envelope({**to_card(record), "content": record["content"]})


@app.patch("/api/v1/rag/files/{file_id}")
async def update_file(file_id: str, payload: RagFileUpdateRequest) -> dict[str, Any]:
    record = store.get(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="RAG file not found")
    if payload.content is not None and not payload.content.strip():
        raise HTTPException(status_code=400, detail="content must not be empty")
    if payload.filename is not None and payload.filename.strip():
        record["filename"] = payload.filename.strip()
    if payload.source is not None and payload.source.strip():
        record["source"] = payload.source.strip()
    if payload.metadata is not None:
        record["metadata"] = deepcopy(payload.metadata)
    if payload.content is not None:
        record["content"] = payload.content
    return envelope(to_card(record))


@app.delete("/api/v1/rag/files/{file_id}")
async def delete_file(file_id: str) -> dict[str, Any]:
    if store.pop(file_id, None) is None:
        raise HTTPException(status_code=404, detail="RAG file not found")
    return envelope(True)


@app.get("/api/v1/rag/search")
async def search(query: str, limit: int = 8) -> dict[str, Any]:
    normalized = query.strip().lower()
    terms = search_terms(query)
    results = []
    for record in store.values():
        content = record["content"]
        haystack = f"{record['filename']}\n{record['source']}\n{content}".lower()
        matches = [term for term in terms if term in haystack]
        exact_match = bool(normalized and normalized in haystack)
        if matches or exact_match:
            score = 1.0 if exact_match else min(0.95, 0.45 + len(matches) / max(len(terms), 1) * 0.5)
            results.append(
                {
                    "chunk_id": f"{record['file_id']}:0",
                    "source_id": record["file_id"],
                    "source_type": "knowledge_doc",
                    "title": record["filename"],
                    "content": content[:500],
                    "score": score,
                    "metadata": {"source": record["source"], **record["metadata"]},
                }
            )
    results.sort(key=lambda item: item["score"], reverse=True)
    return envelope({"query": query, "results": results[:limit]})
