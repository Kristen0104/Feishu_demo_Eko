from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.core.security import AuthContext, get_auth_context
from app.modules.bitable.dependencies import get_bitable_discovery_service, get_bitable_service
from app.modules.bitable.openapi_adapter import BitableOpenApiError
from app.modules.bitable.schemas import (
    BitableArchiveRequest,
    BitableArchiveResponse,
    BitableBaseOption,
    BitableBaseUrlResolveRequest,
    BitableBaseUrlResolveResponse,
    BitableDiscoveryStatus,
    BitableFieldOption,
    BitableInspectResult,
    BitableQueryRequest,
    BitableQueryResponse,
    BitableSchemaResponse,
    BitableSourceCreate,
    BitableSourceSchema,
    BitableSourceUpdate,
    BitableTableOption,
    BitableViewOption,
)
from app.modules.bitable.discovery import BitableDiscoveryService
from app.modules.bitable.service import BitableService
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/discovery/status",
    response_model=ApiResponse[BitableDiscoveryStatus],
    summary="获取当前用户 Bitable 发现状态",
)
async def get_discovery_status(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    discovery_service: Annotated[BitableDiscoveryService, Depends(get_bitable_discovery_service)],
) -> ApiResponse[BitableDiscoveryStatus]:
    return ApiResponse.success(await discovery_service.get_status(auth_context.user_id))


@router.get(
    "/discovery/bases",
    response_model=ApiResponse[list[BitableBaseOption]],
    summary="列出当前用户可选择的多维表格",
)
async def list_discovery_bases(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    discovery_service: Annotated[BitableDiscoveryService, Depends(get_bitable_discovery_service)],
) -> ApiResponse[list[BitableBaseOption]]:
    return ApiResponse.success(await discovery_service.list_bases(auth_context.user_id))


@router.post(
    "/discovery/resolve-url",
    response_model=ApiResponse[BitableBaseUrlResolveResponse],
    summary="通过飞书多维表格链接解析可选择的 Base",
)
async def resolve_discovery_base_url(
    payload: BitableBaseUrlResolveRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    discovery_service: Annotated[BitableDiscoveryService, Depends(get_bitable_discovery_service)],
) -> ApiResponse[BitableBaseUrlResolveResponse]:
    try:
        return ApiResponse.success(await discovery_service.resolve_base_url(auth_context.user_id, payload.url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BitableOpenApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/discovery/tables",
    response_model=ApiResponse[list[BitableTableOption]],
    summary="列出多维表格下的数据表",
)
async def list_discovery_tables(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    discovery_service: Annotated[BitableDiscoveryService, Depends(get_bitable_discovery_service)],
    base_id: str,
) -> ApiResponse[list[BitableTableOption]]:
    try:
        return ApiResponse.success(await discovery_service.list_tables(auth_context.user_id, base_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/discovery/views",
    response_model=ApiResponse[list[BitableViewOption]],
    summary="列出数据表视图",
)
async def list_discovery_views(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    discovery_service: Annotated[BitableDiscoveryService, Depends(get_bitable_discovery_service)],
    base_id: str,
    table_id: str,
) -> ApiResponse[list[BitableViewOption]]:
    try:
        return ApiResponse.success(await discovery_service.list_views(auth_context.user_id, base_id, table_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/discovery/fields",
    response_model=ApiResponse[list[BitableFieldOption]],
    summary="列出数据表字段",
)
async def list_discovery_fields(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    discovery_service: Annotated[BitableDiscoveryService, Depends(get_bitable_discovery_service)],
    base_id: str,
    table_id: str,
) -> ApiResponse[list[BitableFieldOption]]:
    try:
        return ApiResponse.success(await discovery_service.list_fields(auth_context.user_id, base_id, table_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/sources",
    response_model=ApiResponse[list[BitableSourceSchema]],
    summary="列出 Bitable 数据源",
)
async def list_sources(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
    workspace_id: str = Query(default=settings.BITABLE_DEFAULT_WORKSPACE_ID),
) -> ApiResponse[list[BitableSourceSchema]]:
    return ApiResponse.success(await bitable_service.list_sources(workspace_id, created_by=auth_context.user_id))


@router.post(
    "/sources",
    response_model=ApiResponse[BitableSourceSchema],
    summary="新增 Bitable 数据源",
)
async def create_source(
    payload: BitableSourceCreate,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
) -> ApiResponse[BitableSourceSchema]:
    try:
        return ApiResponse.success(await bitable_service.create_source(payload, created_by=auth_context.user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/sources/{source_id}",
    response_model=ApiResponse[BitableSourceSchema],
    summary="更新 Bitable 数据源",
)
async def update_source(
    source_id: str,
    payload: BitableSourceUpdate,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
) -> ApiResponse[BitableSourceSchema]:
    try:
        return ApiResponse.success(await bitable_service.update_source(source_id, payload, created_by=auth_context.user_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/sources/{source_id}",
    response_model=ApiResponse[None],
    summary="删除 Bitable 数据源",
)
async def delete_source(
    source_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
) -> ApiResponse[None]:
    try:
        await bitable_service.delete_source(source_id, created_by=auth_context.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse.success()


@router.post(
    "/sources/{source_id}/inspect",
    response_model=ApiResponse[BitableInspectResult],
    summary="检查 Bitable 数据源结构",
)
async def inspect_source(
    source_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
) -> ApiResponse[BitableInspectResult]:
    try:
        return ApiResponse.success(await bitable_service.inspect_source(source_id, created_by=auth_context.user_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BitableOpenApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/schema",
    response_model=ApiResponse[BitableSchemaResponse],
    summary="获取工作区 Bitable schema 摘要",
)
async def get_schema(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
    workspace_id: str = Query(default=settings.BITABLE_DEFAULT_WORKSPACE_ID),
) -> ApiResponse[BitableSchemaResponse]:
    return ApiResponse.success(BitableSchemaResponse(sources=await bitable_service.list_sources(workspace_id, created_by=auth_context.user_id)))


@router.post(
    "/query",
    response_model=ApiResponse[BitableQueryResponse],
    summary="查询 Bitable 记录",
)
async def query_records(
    payload: BitableQueryRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
) -> ApiResponse[BitableQueryResponse]:
    return ApiResponse.success(await bitable_service.query_records(payload, created_by=auth_context.user_id))


@router.post(
    "/archive",
    response_model=ApiResponse[BitableArchiveResponse],
    summary="归档产物到 Bitable",
)
async def archive_artifact(
    payload: BitableArchiveRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    bitable_service: Annotated[BitableService, Depends(get_bitable_service)],
) -> ApiResponse[BitableArchiveResponse]:
    return ApiResponse.success(await bitable_service.archive_artifact(payload, created_by=auth_context.user_id))
