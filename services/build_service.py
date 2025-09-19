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
        action_type = step.get("type")
        resource_path = os.path.expanduser(os.path.join(self.RESOURCES_FOLDER, resource_name))

        # If action_type is cloudformation, render action script (deploy_cfn.sh.j2) from template folder to resource folder
        if action_type == 'cloudformation':
            action_script = self.DEPLOY_CFN_SCRIPT
            action_template = self.DEPLOY_CFN_TEMPLATE
            action_script_path = os.path.expanduser(os.path.join(self.TEMPLATES_FOLDER, f"{action_script}.j2"))
            action_rendered_script_path = os.path.expanduser(os.path.join(resource_path, action_script))
        # If action_type is terraform, render action script (deploy_cfn.sh.j2) from template folder to resource folder
        elif action_type == 'terraform':
            action_script = self.DEPLOY_TERRAFORM_SCRIPT
            action_template = self.DEPLOY_TERRAFORM_TEMPLATE
            action_script_path = os.path.expanduser(os.path.join(self.TEMPLATES_FOLDER, f"{action_script}.j2"))
            action_rendered_script_path = os.path.expanduser(os.path.join(resource_path, action_script))
        # If action_type is custom-cloudformation, render custom action script (step.get("action_script")) from resource_path folder to resource folder
        elif action_type == 'custom-cloudformation':
            action_script = step.get("action_script")
            action_template = self.DEPLOY_CFN_TEMPLATE
            action_script_path = os.path.expanduser(os.path.join(resource_path, f"{action_script}.j2"))
            action_rendered_script_path = os.path.expanduser(os.path.join(resource_path, action_script))
        # If action_type is custom-terraform, render custom action script (step.get("action_script")) from resource_path folder to resource folder
        elif action_type == 'custom-terraform':
            action_script = step.get("action_script")
            action_template = self.DEPLOY_TERRAFORM_TEMPLATE
            action_script_path = os.path.expanduser(os.path.join(resource_path, f"{action_script}.j2"))
            action_rendered_script_path = os.path.expanduser(os.path.join(resource_path, action_script))
        # If not above cases, always render custom action script from resource folder to resource folder
        else:
            action_script = step.get("action_script")
            action_template = step.get("action_template")
            action_script_path = os.path.expanduser(os.path.join(resource_path, f"{action_script}.j2"))
            action_rendered_script_path = os.path.expanduser(os.path.join(resource_path, action_script))

        logger.debug(f"Determined script_template_path: '{action_script_path}'")
        logger.debug(f"Determined rendered_script_path: '{action_rendered_script_path}'")

        try:
            logger.debug(f"Loading action_script_path: '{action_script_path}'")
            if os.path.exists(action_script_path):
                rendered_script = self.render_template(action_script_path, envs)
                with open(action_rendered_script_path, "w") as f:
                    f.write(rendered_script)
                os.chmod(action_rendered_script_path, 0o755)
            else:
                logger.error("Template path '%s' does not exist after writing for step '%s'.", action_script_path,
                             step.get("action_script"))
                raise RuntimeError(f"Failed to create the rendered template at '{action_rendered_script_path}'.")

            # Here to check if we render cloud template from pre-defined template
            # If not, render custom cloud template from resource folder to resource folder
            if action_type in {"cloudformation", "terraform", "custom-cloudformation", "custom-terraform"}:
                logger.debug("No additional template rendering required for action type: %s", action_type)
                use_template = step.get("use_template", False)
                resource_type = step.get("resource")
                resource_config = step.get("action_config")
                logger.debug("use_template: %s", use_template)
                if action_template:
                    self.render_cloud_template(use_template, action_type, resource_type, resource_config, resource_path, action_template, envs)

        except Exception as e:
            logger.error("Template rendering failed for resource '%s': %s", resource_name, str(e))
            raise RuntimeError(f"Template rendering failed for {resource_name}: {str(e)}") from e

        logger.debug("Executing script for resource '%s': %s", resource_name, action_rendered_script_path)
        result = self.call_subprocess(resource_name, action_rendered_script_path, build_id)
        logger.debug("Step result for resource '%s': %s", resource_name, result)

        # Status update should only happen when execution reaches this point
        self.update_status(resource_name, step.get("name"), result, db, build_id)
        return result

    # Renders cloudformation or terraform templates based on the provided parameters
    # If the value of use_template is True, it will look for predefined templates in the TEMPLATES_FOLDER
    # otherwise, it will look for the template in the resource_path
    # The rendered template will be saved in the resource_path with the name action_template
    # envs is a dictionary containing environment variables to be used in the template rendering
    def render_cloud_template(self, use_template: bool, action_type: str, resource_type: str, resource_config: str, resource_path: str, action_template: str, envs: dict) -> None:
        try:
            if use_template:
                if action_type in {"cloudformation", "terraform"}:
                    template_path = os.path.join(self.TEMPLATES_FOLDER, f"{action_type}", f"{resource_type}", f"{resource_type}.yml.j2")
                    resource_configs_path = os.path.join(resource_path, f"{resource_config}")

                    if not os.path.exists(resource_configs_path):
                        logger.error("Resource config path '%s' does not exist.", resource_configs_path)
                        raise RuntimeError(f"Resource config path '{resource_configs_path}' does not exist.")

                    if not os.path.exists(template_path):
                        logger.error("Template path '%s' does not exist.", template_path)
                        raise RuntimeError(f"Template path '{template_path}' does not exist.")

                    logger.debug("Resource config path: '%s'", resource_configs_path)
                    resource_envs = self.load_yaml(resource_configs_path)
                    logger.info("resource_envs: %s", resource_envs)
                    envs = self.render_and_merge_envs(self, envs, resource_envs)
                else:
                    template_path = os.path.join(resource_path, f"{action_template}.j2")
            else:
                template_path = os.path.join(resource_path, f"{action_template}.j2")

            rendered_template_path = os.path.join(resource_path, action_template)
            if os.path.exists(template_path):
                rendered_template = self.render_template(template_path, envs)
                with open(rendered_template_path, "w") as f:
                    f.write(rendered_template)
            else:
                logger.error("Template path '%s' does not exist for render type '%s'.", template_path, use_template)
                raise RuntimeError(f"Failed to create the rendered template at '{rendered_template_path}'.")
        except Exception as e:
            logger.error("Template rendering failed for render type '%s': %s", use_template, str(e))
            raise RuntimeError(f"Template rendering failed for {use_template}: {str(e)}") from e

    # Executes all steps defined in a task for a given action (e.g., 'build')
    def execute_task(self, task: dict, action: str, db: Session, build_id: str) -> list:
        results = []
        task_name = task.get("name")
        resource_name = task.get("resource")
        steps = task.get("steps", [])
        logger.info("Executing task '%s' for resource: %s (action: %s)", task_name, resource_name, action)
        envs = self.load_config(task)

        logger.debug(f"Finish loading envs ... '{envs}'")

        if not envs:  # Check if envs is empty
            logger.error("Failed to load configuration for task '%s' (resource: %s). Aborting task execution.",
                         task_name, resource_name)
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

    def build(self, component: str, env_path: str, resource_path: str, task_path: str, db: Session) -> BuildResponse:
        # Validate input paths
        if not env_path or not resource_path or not task_path:
            raise ValueError("env_path, resource_path, and task_path must not be None or empty.")
        if not self.ENVIRONMENTS_FOLDER or not self.RESOURCES_FOLDER or not self.TASKS_FOLDER:
            raise ValueError("Service folders (ENVIRONMENTS_FOLDER, RESOURCES_FOLDER, TASKS_FOLDER) must be initialized.")

        # Prepend the new paths to the existing paths
        self.ENVIRONMENTS_FOLDER = os.path.expanduser(os.path.join(env_path, BaseService.ENVIRONMENTS_FOLDER))
        self.RESOURCES_FOLDER = os.path.expanduser(os.path.join(resource_path, BaseService.RESOURCES_FOLDER))
        self.TASKS_FOLDER = os.path.expanduser(os.path.join(task_path, BaseService.TASKS_FOLDER))

        logger.debug("Environments folder set to: %s", self.ENVIRONMENTS_FOLDER)
        logger.debug("Resources folder set to: %s", self.RESOURCES_FOLDER)
        logger.debug("Tasks folder set to: %s", self.TASKS_FOLDER)

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
