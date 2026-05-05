"""
Agent Dependencies - Agent 模块依赖注入
"""
from typing import Annotated

from fastapi import Depends

from app.core.llm_client import LLMClient, get_llm_client
from app.modules.aippt.dependencies import get_aippt_service
from app.modules.aippt.service import AIPPTService
from app.modules.agent.service import AgentService
from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.service import CanvasService
from app.modules.document.dependencies import get_document_service
from app.modules.document.service import DocumentService
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.service import FeishuService
from app.modules.sync.dependencies import get_sync_service
from app.modules.sync.service import SyncService
from app.modules.rag.dependencies import get_rag_service
from app.modules.rag.service import RagService


def get_agent_service(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    feishu_service: Annotated[FeishuService, Depends(get_feishu_service)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    aippt_service: Annotated[AIPPTService, Depends(get_aippt_service)],
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> AgentService:
    """获取 AgentService 实例"""
    return AgentService(
        llm_client=llm_client,
        feishu_service=feishu_service,
        document_service=document_service,
        aippt_service=aippt_service,
        canvas_service=canvas_service,
        sync_service=sync_service,
        rag_service=rag_service,
    )
