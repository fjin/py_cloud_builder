import os
import subprocess
import yaml
import logging
from jinja2 import Environment, FileSystemLoader
from models import Step, Application
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseService:
    USE_DB = False

    TASKS_FOLDER = "tasks"
    RESOURCES_FOLDER = "resources"
    ENVIRONMENTS_FOLDER = "environments"
    TEMPLATES_FOLDER = "templates"
    BUILD_ERROR_MSG = "Build process failed"
    BUILD_SUCCESS_MSG = "Build process completed successfully"
    UNBUILD_ERROR_MSG = "Unbuild process failed"
    UNBUILD_SUCCESS_MSG = "Unbuild process completed successfully"
    SUCCESS_STATE = "success"
    FAILED_STATE = "error"
    DEPLOY_CFN_TEMPLATE = "cfn.yml"
    DEPLOY_TERRAFORM_TEMPLATE = "resources.tf"
    DEPLOY_CFN_SCRIPT = "deploy_cfn.sh"
    DEPLOY_TERRAFORM_SCRIPT = "deploy_terraform.sh"
    DESTROY_CFN_SCRIPT = "destroy_cfn.sh"
    DESTROY_TERRAFORM_SCRIPT = "destroy_terraform.sh"
    CUSTOM_DESTROY_SCRIPT = "destroy.sh"

    @staticmethod
    def flatten_list(nested_list):
        flat_list = []
        for element in nested_list:
            if isinstance(element, list):
                flat_list.extend(BaseService.flatten_list(element))
            else:
                flat_list.append(element)
        return flat_list

    @staticmethod
    def load_yaml(file_path):
        # Expand ~ to the full home directory path
        expanded_path = os.path.expanduser(file_path)
        logger.debug("Loading YAML file: %s", expanded_path)
        if os.path.exists(expanded_path):
            with open(expanded_path, "r") as file:
                try:
                    data = yaml.safe_load(file)
                    logger.debug("YAML file %s loaded successfully.", expanded_path)
                    return data
                except Exception as e:
                    logger.error("Error parsing YAML file %s: %s", expanded_path, e)
                    return {}
        else:
            logger.warning("YAML file %s does not exist.", expanded_path)
        return {}

    @staticmethod
    def merge_envs(global_env, component_env):
        merged = {**global_env, **component_env}
        # logger.debug("Merged environments: %s", merged)
        return merged

    @staticmethod
    def render_template(template_path, context):
        logger.debug("Rendering template: %s with context: %s", template_path, context)
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        template = env.get_template(os.path.basename(template_path))
        rendered = template.render(context)
        logger.debug("Template rendered successfully.")
        return rendered

    @staticmethod
    def call_subprocess(resource_name, script_path, build_id=None) -> dict:
        logger.debug("Calling subprocess for resource: %s with script: %s", resource_name, script_path)
        if os.path.exists(script_path):
            try:
                process = subprocess.run(["bash", script_path], capture_output=True, text=True)
                if process.returncode == 0:
                    results = {"resource": resource_name, "status": "success", "message": process.stdout}
                    logger.debug("Subprocess for resource %s succeeded: %s result: %s", resource_name, process.stdout, results)
                else:
                    results = {"resource": resource_name, "status": "error", "message": process.stderr}
                    logger.error("Subprocess for resource %s failed: %s result: %s", resource_name, process.stderr, results)

            except Exception as e:
                results = {"resource": resource_name, "status": "error", "message": str(e)}
                logger.exception("Exception occurred while executing subprocess for resource %s", resource_name)
        else:
            logger.warning("Script path %s does not exist for resource %s.", script_path, resource_name)
            results = {"resource": resource_name, "status": "error", "message": f"Script path {script_path} does not exist."}
        if build_id:
            results["uuid"] = build_id
        return results

    @staticmethod
    def update_status(task_name, step_name, result, db, build_uuid):
        logger.debug("Updating status for task: %s, step: %s", task_name, step_name)
        step_info = Step(
            task_name=task_name,
            step_name=step_name,
            status=result,
            uuid=build_uuid,
            timestamp=datetime.now()
        )
        db.add(step_info)
        try:
            db.commit()
            logger.debug("Status updated successfully for step: %s", step_name)
        except Exception as e:
            db.rollback()
            logger.exception("Failed to update status for step: %s", step_name)
            raise e

    @staticmethod
    def update_application_record(db, build_id, **kwargs):
        logger.debug("Updating application record with build_id: %s, changes: %s", build_id, kwargs)
        app_record = db.query(Application).filter(Application.uuid == build_id).first()
        if app_record:
            for key, value in kwargs.items():
                setattr(app_record, key, value)
            try:
                db.commit()
                db.refresh(app_record)
                logger.debug("Application record updated: %s", app_record)
                return app_record
            except Exception as e:
                db.rollback()
                logger.exception("Failed to update application record with build_id: %s Exception: %s", build_id, e)
        else:
            logger.warning("No application record found with build_id: %s", build_id)
        return None

    @staticmethod
    def delete_application_record(db, build_id):
        logger.debug("Deleting application record with build_id: %s", build_id)
        app_record = db.query(Application).filter(Application.uuid == build_id).first()
        if app_record:
            try:
                db.delete(app_record)
                db.commit()
                logger.debug("Application record with build_id %s deleted.", build_id)
            except Exception as e:
                db.rollback()
                logger.exception("Failed to delete application record with build_id: %s Exception: %s", build_id, e)

    def load_config(self, task: dict) -> dict:
        resource_name = task.get("resource")
        environment_name = task.get("environment")
        global_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, f"{environment_name}.yml")
        component_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, resource_name, f"{environment_name}.yml")

        global_env_path = os.path.expanduser(global_env_path)
        component_env_path = os.path.expanduser(component_env_path)

        logger.debug("global_env_path: %s", global_env_path)
        logger.debug("component_env_path: %s", component_env_path)

        logger.debug("Loading config for resource: %s, environment: %s", resource_name, environment_name)

        # Check if the global and component environment paths exist
        if not os.path.exists(global_env_path) or not os.path.exists(component_env_path):
            logger.warning(
                "Either global environment path (%s) or component environment path (%s) does not exist.",
                global_env_path, component_env_path
            )
            return {}

        # Load the YAML files
        global_env = self.load_yaml(global_env_path)
        component_env = self.load_yaml(component_env_path)

        # Merge the environments
        merged = self.merge_envs(global_env, component_env)
        # logger.debug("Configuration loaded and merged: %s", merged)

        return merged
