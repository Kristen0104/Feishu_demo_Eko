import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

try:
    from app.core.database import get_db
    from app.core.redis_client import set_cache, get_cache, publish
    from app.core.state_machine import agent_state_machine
    from app.models.models import Session, Task
    from app.schemas.schemas import (
        AgentExecuteRequest,
        AgentStopRequest,
        PptTestRequest,
        PptTestResponse,
    )
    from app.modules.ppt import DeckPlan, DeckRequest
    from app.modules.ppt.strategist import build_deck_plan
    from app.services.intent_service import recognize_intent
    from app.services.llm_service import llm_service
    from app.services.ppt_service import ppt_generation_service
except ModuleNotFoundError:  # pragma: no cover - test import fallback
    from backend.app.core.database import get_db
    from backend.app.core.redis_client import set_cache, get_cache, publish
    from backend.app.core.state_machine import agent_state_machine
    from backend.app.models.models import Session, Task
    from backend.app.schemas.schemas import (
        AgentExecuteRequest,
        AgentStopRequest,
        PptTestRequest,
        PptTestResponse,
    )
    from backend.app.modules.ppt import DeckPlan, DeckRequest
    from backend.app.modules.ppt.strategist import build_deck_plan
    from backend.app.services.intent_service import recognize_intent
    from backend.app.services.llm_service import llm_service
    from backend.app.services.ppt_service import ppt_generation_service

# TODO(PRD-2.1): replace keyword intent routing with structured intent classification and scenario branching.
# TODO(PRD-2.2): inject RAG and Feishu context into the agent pipeline before LLM generation.
# TODO(PRD-2.3): switch task execution into workspace-aware creator/readonly mode.
# TODO(PRD-4.4): emit progress events through backend/app/modules/sync instead of publishing inline here.

BACKEND_ROOT = Path(__file__).resolve().parents[2]
LAYOUTS_INDEX_PATH = BACKEND_ROOT / "vendor" / "ppt_master" / "templates" / "layouts" / "layouts_index.json"

try:
    LAYOUTS_INDEX = json.loads(LAYOUTS_INDEX_PATH.read_text(encoding="utf-8"))
except Exception:
    LAYOUTS_INDEX = {}

router = APIRouter()


SYSTEM_PROMPT = """你是一个智能助手 named Eko，帮助用户处理工作事务。
你擅长：
- 理解和生成文本内容
- 回答问题和提供信息
- 协助制定计划和分析问题

请用简洁、专业的方式回复用户。"""


@router.get("/ppt-templates")
async def list_ppt_templates():
    items = [
        {
            "id": "auto",
            "label": "auto",
            "summary": "根据 prompt 选择外部模板",
            "keywords": [],
        }
    ]
    for template_id, entry in LAYOUTS_INDEX.items():
        items.append(
            {
                "id": template_id,
                "label": entry.get("label") or template_id,
                "summary": entry.get("summary") or "",
                "keywords": entry.get("keywords") or [],
            }
        )
    return {"items": items}


@router.post("/ppt-test", response_model=PptTestResponse)
async def test_ppt_generation(request: PptTestRequest):
    requirement = request.requirement.strip()
    if not requirement and not request.chat_history.strip():
        raise HTTPException(status_code=400, detail="requirement or chat_history is required")

    payload = _build_ppt_payload(request)

    result = await ppt_generation_service.generate(payload)

    return PptTestResponse(
        result=f"已基于原始 prompt 生成 {len(payload['pages'])} 页 PPT。",
        result_url=result.result_url,
        slide_count=len(payload["pages"]),
        generation_mode=request.ppt_mode,
        template_id=str(payload.get("template_name") or "default"),
        template_label=_lookup_template_label(payload.get("template_name")),
    )


@router.post("/execute")
async def execute_agent(
    request: AgentExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    投递指令 - 主入口
    1. 创建/获取会话
    2. 保存用户消息到任务
    3. 调用 LLM 获取回复
    4. 返回结果
    """
    # 获取或创建会话
    session_result = await db.execute(
        select(Session).where(Session.id == request.session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 获取对话历史上下文
    context_key = f"session:{request.session_id}:context"
    existing_context = await get_cache(context_key)
    if existing_context:
        history = json.loads(existing_context)
    else:
        history = []

    # 构建消息列表
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": request.message})

    intent = recognize_intent(request.message)

    # 创建任务记录
    new_task = Task(
        id=None,  # auto-generate
        session_id=request.session_id,
        user_id=session.user_id,
        message=request.message,
        intent=intent,
        status="running",
    )
    db.add(new_task)
    await db.commit()

    # 更新会话状态
    session.last_intent = intent
    await db.commit()

    try:
        result = await llm_service.chat(
            messages=messages,
            stream=False,
            system_prompt=SYSTEM_PROMPT,
        )
        content = result["content"]
        result_url = None
    except Exception as e:
        content = f"抱歉，发生了错误: {str(e)}"
        new_task.status = "failed"
        new_task.result = content
        await db.commit()
        raise HTTPException(status_code=500, detail=content)

    # 更新任务状态和结果
    new_task.result = content
    new_task.status = "completed"
    await db.commit()

    # 更新上下文缓存
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": content})
    if len(history) > 10:
        history = history[-10:]
    await set_cache(context_key, json.dumps(history, ensure_ascii=False), expire=300)

    # 广播完成事件
    await publish(f"session:{request.session_id}", json.dumps({
        "type": "TASK_COMPLETED",
        "payload": {
            "task_id": new_task.id,
            "intent": intent,
            "result": content,
            "result_url": result_url,
            "generation_mode": None,
            "template_id": None,
        }
    }, ensure_ascii=False))

    return {
        "task_id": new_task.id,
        "session_id": request.session_id,
        "intent": intent,
        "status": "completed",
        "result": content,
        "result_url": result_url,
    }

@router.post("/stop")
async def stop_agent(
    request: AgentStopRequest,
    db: AsyncSession = Depends(get_db),
):
    """强制中断当前正在运行的 Agent 任务"""
    task_result = await db.execute(
        select(Task).where(Task.id == request.task_id)
    )
    task = task_result.scalar_one_or_none()
    if task:
        task.status = "cancelled"
        await db.commit()

    agent_state_machine.reset()
    return {"status": "stopped"}


@router.get("/tasks/{task_id}/plan")
async def get_task_plan(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取当前任务被拆解后的 JSON 步骤"""
    task_result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "steps": task.plan_steps or []
    }


@router.get("/history")
async def get_task_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取该会话下的所有指令与执行结果历史"""
    result = await db.execute(
        select(Task).where(
            Task.session_id == session_id,
        ).order_by(Task.created_at.desc()).limit(50)
    )
    tasks = result.scalars().all()

    return {
        "items": [
            {
                "id": t.id,
                "message": t.message,
                "result": t.result,
                "intent": t.intent,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in tasks
        ]
    }


def _lookup_template_label(template_id: str | None) -> str | None:
    if not template_id:
        return None
    entry = LAYOUTS_INDEX.get(template_id)
    if not entry:
        return template_id
    return entry.get("label") or template_id


def _build_ppt_payload(request: PptTestRequest) -> dict[str, object]:
    prompt_text = request.requirement.strip() or request.chat_history.strip()
    deck_request = DeckRequest(
        raw_prompt=prompt_text,
        chat_history=request.chat_history,
        generation_mode=request.ppt_mode,
        template_preference=request.ppt_template,
    )
    deck_plan = build_deck_plan(deck_request)
    return {
        "project_name": deck_plan.project_name,
        "deck_plan": deck_plan,
        "pages": _build_generation_pages(deck_plan),
        "template_name": deck_plan.template_id,
    }


def _build_generation_pages(plan: DeckPlan) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []
    total_pages = len(plan.pages)
    agenda_items = [page.title for page in plan.pages if page.page_type == "content"]
    product_name = plan.pages[0].title if plan.pages else plan.project_name

    for page in plan.pages:
        if page.page_type == "cover":
            pages.append(
                {
                    "layout": "cover",
                    "page_type": page.page_type,
                    "page_rhythm": page.page_rhythm,
                    "title": page.title,
                    "subtitle": _brief_to_subtitle(page.brief),
                    "speaker_name": "Eko Presenter",
                    "speaker_title": "Auto-generated deck",
                    "date": "2026",
                    "footer": "2026",
                }
            )
        elif page.page_type == "toc":
            pages.append(
                {
                    "layout": "toc",
                    "page_type": page.page_type,
                    "page_rhythm": page.page_rhythm,
                    "title": page.title,
                    "toc_items": agenda_items or _content_points_from_brief(page.brief),
                    "STATS_AREA": f"{product_name} · {total_pages} 页演示",
                }
            )
        elif page.page_type == "chapter":
            pages.append(
                {
                    "layout": "chapter",
                    "page_type": page.page_type,
                    "page_rhythm": page.page_rhythm,
                    "title": page.title,
                    "section": "第一章",
                    "chapter_num": "01",
                    "chapter_title": page.title,
                    "chapter_title_en": "Section overview",
                    "subtitle": _brief_to_subtitle(page.brief),
                }
            )
        elif page.page_type == "ending":
            pages.append(
                {
                    "layout": "ending",
                    "page_type": page.page_type,
                    "page_rhythm": page.page_rhythm,
                    "title": page.title,
                    "subtitle": _brief_to_subtitle(page.brief),
                    "thank_you": page.title,
                    "ending_subtitle": _brief_to_subtitle(page.brief),
                    "thanks_items": ["产品设计", "工程实现", "发布团队"],
                    "thanks_reason_1": "结构规划",
                    "thanks_reason_2": "内容整理",
                    "thanks_reason_3": "演示生成",
                    "footer": page.title,
                }
            )
        else:
            pages.append(
                {
                    "layout": "content",
                    "page_type": page.page_type,
                    "page_rhythm": page.page_rhythm,
                    "title": page.title,
                    "content": _content_points_from_brief(page.brief),
                    "page_num": f"{page.index:02d}",
                    "footer": f"{product_name} 发布会",
                }
            )

    return pages


def _brief_to_subtitle(brief: str) -> str:
    parts = _content_points_from_brief(brief)
    return " · ".join(parts[:2]) if parts else brief


def _content_points_from_brief(brief: str) -> list[str]:
    normalized = (
        brief.replace("｜", "|")
        .replace("•", "|")
        .replace("；", "|")
        .replace("，", "|")
        .replace("/", "|")
    )
    parts = [part.strip() for part in normalized.split("|") if part.strip()]
    return parts or ["亮点提炼", "价值表达", "使用场景"]
