import os
import uuid
import logging
from sqlalchemy.orm import Session
from services.base_service import BaseService
from models import Application
from schemas import BuildResponse

logger = logging.getLogger(__name__)


class BuildService(BaseService):

    def run_step(self, resource_name: str, step: dict, envs: dict, db: Session, build_id: str) -> dict:
        logger.debug("Running step for resource: %s", resource_name)
        action_script = step.get("action_script")
        action_type = step.get("type")
        resource_path = os.path.join(self.RESOURCES_FOLDER, resource_name)
        script_template_path = os.path.join(resource_path, f"{action_script}.j2")
        rendered_script_path = os.path.join(resource_path, action_script)

        try:
            logger.debug(f"Loading script_template_path: '{script_template_path}'")
            if os.path.exists(script_template_path):
                rendered_script = self.render_template(script_template_path, envs)
                with open(rendered_script_path, "w") as f:
                    f.write(rendered_script)
                os.chmod(rendered_script_path, 0o755)
            else:
                logger.error("Template path '%s' does not exist after writing for step '%s'.", script_template_path, step.get("action_script"))
                raise RuntimeError(f"Failed to create the rendered template at '{script_template_path}'.")

            if action_type != "shell":
                action_template = step.get("action_template")
                if action_template:
                    template_path = os.path.join(resource_path, f"{action_template}.j2")
                    rendered_template_path = os.path.join(resource_path, action_template)
                    if os.path.exists(template_path):
                        rendered_template = self.render_template(template_path, envs)
                        with open(rendered_template_path, "w") as f:
                            f.write(rendered_template)
                    else:
                        logger.error("Template path '%s' does not exist after writing for step '%s'.", template_path, step.get("action_script"))
                        raise RuntimeError(f"Failed to create the rendered template at '{template_path}'.")

        except Exception as e:
            logger.error("Template rendering failed for resource '%s': %s", resource_name, str(e))
            raise RuntimeError(f"Template rendering failed for {resource_name}: {str(e)}") from e

        result = self.call_subprocess(resource_name, rendered_script_path, build_id)
        logger.debug("Step result for resource '%s': %s", resource_name, result)

        # Status update should only happen when execution reaches this point
        self.update_status(resource_name, step.get("name"), result, db, build_id)
        return result

    def execute_task(self, task: dict, action: str, db: Session, build_id: str) -> list:
        results = []
        task_name = task.get("name")
        resource_name = task.get("resource")
        steps = task.get("steps", [])
        logger.info("Executing task '%s' for resource: %s (action: %s)", task_name, resource_name, action)
        envs = self.load_config(task)

        logger.debug(f"Finish loading envs ... '{envs}'")

        if not envs:  # Check if envs is empty
            logger.error("Failed to load configuration for task '%s' (resource: %s). Aborting task execution.", task_name, resource_name)
            return []  # Return an empty list if configuration loading failed

        logger.debug("Start executing steps ...")
        for step in steps:
            try:
                result = self.run_step(resource_name, step, envs, db, build_id)
                results.append(result)
            except Exception as e:
                logger.error("Step '%s' failed with error: %s", step.get("name"), str(e))
                return []  # Return an empty list if any step fails

        return self.flatten_list(results)

    def build(self, component: str, db: Session) -> BuildResponse:
        active_build = db.query(Application).filter(
            Application.application_name == component,
            Application.status == "started"
        ).first()
        if active_build:
            logger.error("Build already in progress for component '%s' (UUID: %s)", component, active_build.uuid)
            return BuildResponse(
                status=BaseService.FAILED_STATE,
                message=f"Build for component '{component}' is already in progress.",
                component=component,
                uuid="",  # instead of None
                results=[]
            )

        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")
        tasks = self.load_yaml(yaml_path)
        if not tasks:
            logger.error("Task file '%s.yml' not found.", component)
            return BuildResponse(
                status=BaseService.FAILED_STATE,
                message=f"Task file {component}.yml not found",
                component=component,
                uuid="",  # instead of None
                results=[]
            )

        build_id = str(uuid.uuid4())
        logger.info("Starting build for '%s' with build_id: %s", component, build_id)

        # Create the application record but do not commit yet
        new_app = Application(
            uuid=build_id,
            application_name=component,
            action="build",
            status="started"
        )
        db.add(new_app)

        results = []
        overall_error = False

        try:
            for task in tasks:
                task_results = self.execute_task(task, "build", db, build_id)

                if not task_results:
                    logger.error("Task execution failed for task '%s'. No results returned.", task.get("name"))
                    new_app.status = BaseService.FAILED_STATE
                    new_app.tasks_built = [task.get("name")]
                    db.commit()
                    return BuildResponse(
                        status=BaseService.FAILED_STATE,
                        message=f"Task execution failed for task {task.get('name')}. No results returned",
                        component=component,
                        uuid=build_id,
                        results=[]
                    )

                if any(r.get("status") == BaseService.FAILED_STATE for r in task_results if isinstance(r, dict)):
                    overall_error = True
                results.append(task_results)

            # If all tasks pass, update the database with a success status
            new_app.status = BaseService.SUCCESS_STATE if not overall_error else BaseService.FAILED_STATE
            new_app.tasks_built = [task.get("name") for task in tasks]
            db.commit()

        except RuntimeError as e:
            logger.error("Build process aborted due to error: %s", str(e))
            db.rollback()  # Undo any changes since a commit has not happened yet
            return BuildResponse(
                status=BaseService.FAILED_STATE,
                message=f"{BaseService.BUILD_ERROR_MSG}: {str(e)}",
                component=component,
                uuid=build_id,
                results=[]
            )

        results = self.flatten_list(results)
        logger.info("Build for '%s' completed with status: %s", component, new_app.status)

        if not overall_error:
            state = BaseService.SUCCESS_STATE
            message = BaseService.BUILD_SUCCESS_MSG
        else:
            state = BaseService.FAILED_STATE
            message = BaseService.BUILD_ERROR_MSG
        return BuildResponse(
            status=state,
            message=message,
            component=component,
            uuid=build_id,
            results=results
        )
