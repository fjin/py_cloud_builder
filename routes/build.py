from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import BuildRequest, BuildResponse
from services.build_service import BuildService
import logging

router = APIRouter()
build_service = BuildService()
logger = logging.getLogger(__name__)


@router.post("/", response_model=BuildResponse)
def trigger_build(request: BuildRequest, db: Session = Depends(get_db)):
    if not request.component:
        raise HTTPException(status_code=400, detail="Component name is required")
    try:
        result = build_service.build(request.component, db)
        if not isinstance(result, BuildResponse):
            raise HTTPException(status_code=500, detail="Invalid build response")
        return result
    except Exception as e:
        logger.exception("Unexpected error occurred during build: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
