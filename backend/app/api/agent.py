import json

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.redis_client import set_cache, get_cache, publish
from app.core.state_machine import AgentState, agent_state_machine
from app.models.models import Session, Task
from app.schemas.schemas import AgentExecuteRequest, AgentStopRequest
from app.services.llm_service import llm_service

router = APIRouter()


SYSTEM_PROMPT = """你是一个智能助手 named Eko，帮助用户处理工作事务。
你擅长：
- 理解和生成文本内容
- 回答问题和提供信息
- 协助制定计划和分析问题

请用简洁、专业的方式回复用户。"""


@router.post("/execute")
async def execute_agent(
    request: AgentExecuteRequest,
    user_id: str = Depends(get_current_user_id),
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
        select(Session).where(Session.id == request.session_id, Session.user_id == user_id)
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

    # 创建任务记录
    new_task = Task(
        id=None,  # auto-generate
        session_id=request.session_id,
        user_id=user_id,
        message=request.message,
        intent="CHAT",  # 简化：直接设为闲聊模式
        status="running",
    )
    db.add(new_task)
    await db.commit()

    # 更新会话状态
    session.last_intent = "CHAT"
    await db.commit()

    # 调用 LLM
    try:
        result = await llm_service.chat(
            messages=messages,
            stream=False,
            system_prompt=SYSTEM_PROMPT,
        )
        content = result["content"]
    except Exception as e:
        content = f"抱歉，发生了错误: {str(e)}"
        new_task.status = "failed"
        await db.commit()

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
        "payload": {"task_id": new_task.id, "result": content}
    }, ensure_ascii=False))

    return {
        "task_id": new_task.id,
        "session_id": request.session_id,
        "status": "completed",
        "result": content,
    }


@router.post("/stop")
async def stop_agent(
    request: AgentStopRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """强制中断当前正在运行的 Agent 任务"""
    task_result = await db.execute(
        select(Task).where(Task.id == request.task_id, Task.user_id == user_id)
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
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取当前任务被拆解后的 JSON 步骤"""
    task_result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
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
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取该会话下的所有指令与执行结果历史"""
    result = await db.execute(
        select(Task).where(
            Task.session_id == session_id,
            Task.user_id == user_id
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
