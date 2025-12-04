import os
import logging
import json
from schemas import EnvironmentResponse
from services.base_service import BaseService

logger = logging.getLogger(__name__)


class EnvironmentService(BaseService):
    def get_environment(self, component: str, env_path: str, resource_path: str, task_path: str) -> EnvironmentResponse:
        # Validate input paths
        if not self.ENVIRONMENTS_FOLDER or not self.RESOURCES_FOLDER or not self.TASKS_FOLDER:
            raise ValueError("Service folders (ENVIRONMENTS_FOLDER, RESOURCES_FOLDER, TASKS_FOLDER) must be initialized.")

        # If any of the paths are empty, default to current working directory
        if not env_path:
            env_path = os.getcwd()
        if not resource_path:
            resource_path = os.getcwd()
        if not task_path:
            task_path = os.getcwd()

        # Prepend the new paths to the existing paths
        self.ENVIRONMENTS_FOLDER = os.path.expanduser(os.path.join(env_path, BaseService.ENVIRONMENTS_FOLDER))
        self.RESOURCES_FOLDER = os.path.expanduser(os.path.join(resource_path, BaseService.RESOURCES_FOLDER))
        self.TASKS_FOLDER = os.path.expanduser(os.path.join(task_path, BaseService.TASKS_FOLDER))

        logger.debug("Environments folder set to: %s", self.ENVIRONMENTS_FOLDER)
        logger.debug("Resources folder set to: %s", self.RESOURCES_FOLDER)
        logger.debug("Tasks folder set to: %s", self.TASKS_FOLDER)

        env_vars = {}  # Initialize the dictionary

        # Load environment variables from YAML file
        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")
        tasks = self.load_yaml(yaml_path)
        if not tasks:
            logger.error("Task file '%s.yml' not found.", component)
            return EnvironmentResponse(
                status=BaseService.FAILED_STATE,
                message=f"Task file {component}.yml not found",
                component=component,
                environment={}
            )

        # Process each task and its steps
        for task in tasks:
            resource_name = task.get("resource")
            steps = task.get("steps", [])
            env_vars = self.load_config(task)

            for step in steps:
                resource_path = os.path.expanduser(os.path.join(self.RESOURCES_FOLDER, resource_name))
                use_template = step.get("use_template", False)
                if use_template:
                    resource_config = step.get("action_config")
                    resource_configs_path = os.path.join(resource_path, f"{resource_config}")
                    resource_envs = self.load_yaml(resource_configs_path)
                    env_vars = self.render_and_merge_envs(self, env_vars, resource_envs)

        logger.debug("Environmental variables: %s", json.dumps(env_vars, indent=2))

        return EnvironmentResponse(
            component=component,
            status="success",
            message="Environment loaded",
            environment=env_vars
        )
