from fastapi import APIRouter, HTTPException
from schemas import UnBuildRequest, UnBuildResponse
from services.build_service import BuildService

router = APIRouter()
build_service = BuildService()

@router.post("/", response_model=UnBuildResponse)
def trigger_build(request: UnBuildRequest):
    if not request.component:
        raise HTTPException(status_code=400, detail="Component name is required")

    result = build_service.unbuild(request.component)
    return result