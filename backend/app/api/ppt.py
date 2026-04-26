"""PPT generation API."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.schemas import PptGenerateRequest, PptGenerateResponse
from app.services.ppt_service import ppt_generation_service

router = APIRouter()


@router.post("/generate", response_model=PptGenerateResponse)
async def generate_ppt(request: PptGenerateRequest):
    try:
        result = await ppt_generation_service.generate(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return PptGenerateResponse(
        project_name=result.project_name,
        project_path=str(result.project_path),
        output_path=str(result.output_path),
        result_url=result.result_url,
    )
