from pydantic import BaseModel, EmailStr
from typing import List

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True

class EnvironmentCreate(BaseModel):
    name: str
    status: str

class EnvironmentResponse(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        from_attributes = True  # Ensures compatibility with SQLAlchemy models


class ResourceCreate(BaseModel):
    name: str
    status: str

class ResourceResponse(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        from_attributes = True  # Ensures compatibility with SQLAlchemy models

class ResourceResult(BaseModel):
    resource: str
    status: str
    message: str

class BuildRequest(BaseModel):
    component: str

class BuildResponse(BaseModel):
    component: str
    status: str  # <-- This is missing in your response
    message: str  # <-- This is missing in your response
    results: List[ResourceResult]

class UnBuildRequest(BaseModel):
    component: str

class UnBuildResponse(BaseModel):
    component: str
    status: str  # <-- This is missing in your response
    message: str  # <-- This is missing in your response
    results: List[ResourceResult]