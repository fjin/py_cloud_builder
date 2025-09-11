from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import UnBuildRequest, UnBuildResponse
from services.unbuild_service import UnbuildService

router = APIRouter()
unbuild_service = UnbuildService()


@router.post("/", response_model=UnBuildResponse)
def trigger_unbuild(request: UnBuildRequest, db: Session = Depends(get_db)):
    if not request.component:
        raise HTTPException(status_code=400, detail="Component name is required")

    result = unbuild_service.unbuild(request.component, request.db_flag, db)
    return result
