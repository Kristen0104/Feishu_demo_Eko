from __future__ import annotations

from app.config import get_settings
from app.modules.feishu.client import FeishuClient, HttpxFeishuHttpClient
from app.modules.feishu.service import FeishuService


def get_feishu_http_client() -> HttpxFeishuHttpClient:
    return HttpxFeishuHttpClient()


def get_feishu_client() -> FeishuClient:
    settings = get_settings()
    return FeishuClient(
        http_client=get_feishu_http_client(),
        app_id=settings.FEISHU_APP_ID,
        app_secret=settings.FEISHU_APP_SECRET,
        document_endpoint_template=settings.FEISHU_DOC_RESOLVE_ENDPOINT_TEMPLATE,
        raw_content_endpoint_template=settings.FEISHU_DOC_RAW_CONTENT_ENDPOINT_TEMPLATE,
        document_blocks_endpoint_template=settings.FEISHU_DOC_BLOCKS_ENDPOINT_TEMPLATE,
        whiteboard_nodes_endpoint_template=settings.FEISHU_WHITEBOARD_NODES_ENDPOINT_TEMPLATE,
        whiteboard_publish_endpoint_template=settings.FEISHU_WHITEBOARD_PUBLISH_ENDPOINT_TEMPLATE,
        whiteboard_theme_update_endpoint_template=(
            settings.FEISHU_WHITEBOARD_THEME_UPDATE_ENDPOINT_TEMPLATE
        ),
        whiteboard_syntax_import_endpoint_template=(
            settings.FEISHU_WHITEBOARD_SYNTAX_IMPORT_ENDPOINT_TEMPLATE
        ),
        access_token_provider=(
            (lambda: settings.FEISHU_DOC_ACCESS_TOKEN)
            if settings.FEISHU_DOC_ACCESS_TOKEN
            else None
        ),
    )


def get_feishu_service() -> FeishuService:
    return FeishuService(client=get_feishu_client())
