from fastapi import APIRouter, HTTPException
from schemas import EnvironmentResponse
from services.environment_service import EnvironmentService

router = APIRouter()
service = EnvironmentService()


@router.get("/", response_model=EnvironmentResponse)
def get_environment(component: str, env_path: str, resource_path: str, task_path: str):
    result = service.get_environment(component, env_path, resource_path, task_path)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
