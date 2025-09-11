import os
import logging
import uuid

from sqlalchemy.orm import Session
from services.base_service import BaseService
from models import Application
from schemas import UnBuildResponse

logger = logging.getLogger(__name__)


class UnbuildService(BaseService):

    def destroy_task(self, task: dict, db: Session, build_id: str) -> dict:
        resource = task.get("resource")
        resource_path = os.path.join(self.RESOURCES_FOLDER, resource)
        destroy_template_path = os.path.join(resource_path, "destroy.sh.j2")
        destroy_script_path = os.path.join(resource_path, "destroy.sh")
        logger.debug("Preparing to destroy resource '%s'", resource)

        # Load environment for the task.
        envs = self.load_config(task)
        if os.path.exists(destroy_template_path):
            logger.debug("Found destroy template for resource '%s': %s", resource, destroy_template_path)
            rendered_destroy_script = self.render_template(destroy_template_path, envs)
            with open(destroy_script_path, "w") as f:
                f.write(rendered_destroy_script)
            os.chmod(destroy_script_path, 0o755)
        else:
            logger.warning("No destroy template for resource '%s'. Using existing destroy.sh if available.", resource)

        result = self.call_subprocess(resource, destroy_script_path, build_id)
        logger.debug("Destroy result for resource '%s': %s", resource, result)
        self.update_status(resource, "destroy", result, db, build_id)
        return result

    def execute_task(self, task: dict, db: Session, build_id: str) -> list:
        results = []
        task_name = task.get("name")
        logger.info("Executing unbuild task: %s", task_name)
        # Only infra can be destroyed
        if task.get("type") == "infrastructure":
            result = self.destroy_task(task, db, build_id)
            self.update_status(task.get("resource"), task_name, result, db, build_id)
            results.append(result)
        return results

    def unbuild(self, component: str, use_db: bool, db: Session) -> UnBuildResponse:
        logger.info("Starting unbuild for component: %s", component)
        results = []
        # Check if a component exists
        if not os.path.exists(os.path.join(self.TASKS_FOLDER, f"{component}.yml")):
            logger.error("Task file '%s.yml' not found for unbuild.", component)
            return UnBuildResponse(
                status=BaseService.FAILED_STATE,
                message=f"Task file {component}.yml not found",
                component=component,
                uuid="",  # instead of None
                results=results
            )

        # Locker check for active unbuild.
        existing_unbuild = db.query(Application).filter(
            Application.application_name == component,
            Application.action == "unbuild",
            Application.status == "started"
        ).first()
        if existing_unbuild:
            logger.error("Unbuild already in progress for '%s' (UUID: %s)", component, existing_unbuild.uuid)
            return UnBuildResponse(
                status=BaseService.FAILED_STATE,
                message=f"An unbuild for component '{component}' is already in progress.",
                component=component,
                uuid=str(existing_unbuild.uuid),
                results=results
            )

        app_record = db.query(Application).filter(
            Application.application_name == component
        ).order_by(Application.timestamp.desc()).first()

        if not app_record and use_db is True:
            logger.error("No build record found for component: %s", component)
            return UnBuildResponse(
                status=BaseService.FAILED_STATE,
                message=f"No build record found for component {component}",
                component=component,
                uuid="",
                results=results
            )

        if app_record and use_db is True:
            build_id = app_record.uuid
            logger.info("Using build_id '%s' for unbuild of component: %s", build_id, component)
        else:
            build_id = str(uuid.uuid4())
            logger.info("Using generated build_id '%s' for unbuild of component: %s", build_id, component)

        self.update_application_record(db, build_id, action="unbuild", status="started")

        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")
        tasks = self.load_yaml(yaml_path)
        if not tasks:
            logger.error("Task file '%s.yml' not found for unbuild.", component)
            self.update_application_record(db, build_id, status="failed")
            return UnBuildResponse(
                status=BaseService.FAILED_STATE,
                message=f"Task file {component}.yml not found",
                component=component,
                uuid=build_id,  # instead of None
                results=results
            )

        overall_error = False
        for task in tasks:
            task_results = self.execute_task(task, db, build_id)
            if any(r.get("status") == BaseService.FAILED_STATE for r in task_results if isinstance(r, dict)):
                overall_error = True
            results.extend(task_results)

        if overall_error:
            logger.error("Unbuild process failed for component: %s", component)
            self.update_application_record(db, build_id, status="failed")

            return UnBuildResponse(
                status=BaseService.FAILED_STATE,
                message=BaseService.UNBUILD_ERROR_MSG,
                component=component,
                uuid=build_id,
                results=results
            )
        else:
            logger.info("Unbuild process completed successfully for component: %s", component)
            self.delete_application_record(db, build_id)
            return UnBuildResponse(
                status=BaseService.SUCCESS_STATE,
                message=BaseService.UNBUILD_SUCCESS_MSG,
                component=component,
                uuid=build_id,
                results=results
            )
