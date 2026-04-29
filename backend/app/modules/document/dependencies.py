"""
Document Dependencies - 文档模块依赖注入
"""
from app.core.llm_client import get_llm_client
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.document.service import DocumentService


def get_document_service(
    llm_client = None,
    feishu_service = None,
):
    """获取文档服务实例"""
    return DocumentService(
        llm_client=llm_client or get_llm_client(),
        feishu_service=feishu_service or get_feishu_service(),
    )
