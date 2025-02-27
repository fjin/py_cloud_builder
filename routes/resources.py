from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Resource
from schemas import ResourceCreate, ResourceResponse
from typing import List

router = APIRouter()

# Create a new resource
@router.post("/", response_model=ResourceResponse)
def create_resource(resource: ResourceCreate, db: Session = Depends(get_db)):
    db_resource = db.query(Resource).filter(Resource.name == resource.name).first()
    if db_resource:
        raise HTTPException(status_code=400, detail="Resource name already exists")

    new_resource = Resource(name=resource.name, status=resource.status)
    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)
    return new_resource

# Get all resources
@router.get("/", response_model=List[ResourceResponse])
def get_resources(db: Session = Depends(get_db)):
    resources = db.query(Resource).all()
    if not resources:
        return []

    return resources
