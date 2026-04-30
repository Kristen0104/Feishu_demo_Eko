"""
Agent Dependencies - Agent 模块依赖注入
"""
from typing import Annotated

from fastapi import Depends

from app.core.llm_client import LLMClient, get_llm_client
from app.modules.agent.service import AgentService
from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.service import CanvasService
from app.modules.document.dependencies import get_document_service
from app.modules.document.service import DocumentService
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.service import FeishuService
from app.modules.ppt.dependencies import get_ppt_service
from app.modules.ppt.service import PptService


def get_agent_service(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    ppt_service: Annotated[PptService, Depends(get_ppt_service)],
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> AgentService:
    """获取 AgentService 实例"""
    return AgentService(
        llm_client=llm_client,
        feishu_service=feishu_service,
        document_service=document_service,
        ppt_service=ppt_service,
        canvas_service=canvas_service,
    )
