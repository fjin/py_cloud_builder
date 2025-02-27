from fastapi import APIRouter, HTTPException
from schemas import BuildRequest, BuildResponse
from services.build_service import BuildService

router = APIRouter()
build_service = BuildService()

@router.post("/", response_model=BuildResponse)
def trigger_build(request: BuildRequest):
    if not request.component:
        raise HTTPException(status_code=400, detail="Component name is required")

    result = build_service.build(request.component)
    return result