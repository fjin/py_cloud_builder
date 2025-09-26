from pydantic import BaseModel
from typing import Dict, List


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


class EnvironmentResponse(BaseModel):
    component: str
    status: str
    message: str
    environment: Dict  # Contains all loaded env variables


class BuildRequest(BaseModel):
    component: str
    env_path: str
    resource_path: str
    task_path: str
    db_flag: bool = False


class BuildResponse(BaseModel):
    component: str
    status: str  # <-- This is missing in your response
    message: str  # <-- This is missing in your response
    uuid: str
    results: List[ResourceResult]


class UnBuildRequest(BaseModel):
    component: str
    task_path: str
    db_flag: bool = False


class UnBuildResponse(BaseModel):
    component: str
    status: str  # <-- This is missing in your response
    message: str  # <-- This is missing in your response
    uuid: str
    results: List[ResourceResult]


class StepResponse(BaseModel):
    id: int
    task_name: str
    step_name: str
    status: Dict  # This contains the full result info as JSON
    uuid: str

    class Config:
        orm_mode = True


class StatusResponse(BaseModel):
    uuid: str
    application_name: str
    status: str
    action: str
    message: str
    steps: List[StepResponse]
