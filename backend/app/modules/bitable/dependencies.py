from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.config import Settings, get_settings
from app.modules.auth.dependencies import get_auth_provider, get_auth_repository
from app.modules.auth.provider import FeishuOAuthProvider
from app.modules.auth.repository import AuthRepository
from app.modules.bitable.discovery import BitableBaseResolver, BitableDiscoveryService
from app.modules.bitable.openapi_adapter import BitableOpenApiAdapter
from app.modules.bitable.repository import BitableRepository
from app.modules.bitable.service import BitableService
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.dependencies import get_feishu_client
from app.modules.feishu.identity_service import FeishuIdentityService


def get_bitable_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> BitableRepository:
    return BitableRepository(db)


def get_feishu_identity_service(
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    provider: Annotated[FeishuOAuthProvider, Depends(get_auth_provider)],
) -> FeishuIdentityService:
    return FeishuIdentityService(repository, provider)


def get_bitable_base_resolver(
    repository: Annotated[BitableRepository, Depends(get_bitable_repository)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> BitableBaseResolver:
    return BitableBaseResolver(repository, settings=app_settings)


def get_bitable_service(
    repository: Annotated[BitableRepository, Depends(get_bitable_repository)],
    feishu_client: Annotated[FeishuClient, Depends(get_feishu_client)],
    base_resolver: Annotated[BitableBaseResolver, Depends(get_bitable_base_resolver)],
    identity_service: Annotated[FeishuIdentityService, Depends(get_feishu_identity_service)],
) -> BitableService:
    return BitableService(
        repository,
        adapter=BitableOpenApiAdapter(feishu_client=feishu_client),
        base_resolver=base_resolver,
        identity_service=identity_service,
    )


def get_bitable_discovery_service(
    identity_service: Annotated[FeishuIdentityService, Depends(get_feishu_identity_service)],
    base_resolver: Annotated[BitableBaseResolver, Depends(get_bitable_base_resolver)],
    feishu_client: Annotated[FeishuClient, Depends(get_feishu_client)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> BitableDiscoveryService:
    return BitableDiscoveryService(
        identity_service,
        base_resolver,
        adapter=BitableOpenApiAdapter(feishu_client=feishu_client),
        settings=app_settings,
    )
