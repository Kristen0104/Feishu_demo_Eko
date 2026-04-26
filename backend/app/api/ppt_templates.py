"""Template pack import/list API."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.schemas import PptTemplateImportRequest, PptTemplateImportResponse
from app.services.ppt_template_service import ppt_template_service

router = APIRouter()


@router.post("/import", response_model=PptTemplateImportResponse)
async def import_templates(request: PptTemplateImportRequest):
    try:
        packs = ppt_template_service.import_sources(
            source_paths=request.source_paths,
            collection_name=request.collection_name,
            preferred_template=request.preferred_template,
            style_group=request.style_group,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return PptTemplateImportResponse(
        packs=[
            {
                "pack_dir": str(pack.pack_dir),
                "source_pptx": str(pack.source_pptx),
                "base_template": pack.base_template,
                "manifest_path": str(pack.manifest_path),
            }
            for pack in packs
        ]
    )


@router.get("")
async def list_templates():
    return {"items": ppt_template_service.list_packs()}
