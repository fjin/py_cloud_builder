from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import StatusResponse  # Now this import will work
from services.status_service import StatusService

router = APIRouter()
status_service = StatusService()


@router.get("/", response_model=StatusResponse)
def get_status(application_name: str, db: Session = Depends(get_db)):
    result = status_service.get_status(application_name, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
