from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Environment
from schemas import EnvironmentCreate, EnvironmentResponse
from typing import List

router = APIRouter()

# Create a new environment
@router.post("/", response_model=EnvironmentResponse)
def create_environment(env: EnvironmentCreate, db: Session = Depends(get_db)):
    db_env = db.query(Environment).filter(Environment.name == env.name).first()
    if db_env:
        raise HTTPException(status_code=400, detail="Environment name already exists")

    new_env = Environment(name=env.name, status=env.status)
    db.add(new_env)
    db.commit()
    db.refresh(new_env)
    return new_env

# Get all environments
@router.get("/", response_model=List[EnvironmentResponse])
def get_environments(db: Session = Depends(get_db)):
    environments = db.query(Environment).all()
    if not environments:
        return []

    return environments
