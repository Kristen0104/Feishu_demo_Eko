from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.shared.responses import ApiResponse

router = APIRouter()


@router.get(
    "/system/ping",
    response_model=ApiResponse[dict[str, str]],
    summary="系统健康检查骨架",
)
async def ping() -> ApiResponse[dict[str, str]]:
    return ApiResponse.success(
        {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
