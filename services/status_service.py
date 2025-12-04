import logging
from sqlalchemy.orm import Session
from models import Application, Step
from schemas import StatusResponse
from services.base_service import BaseService

logger = logging.getLogger(__name__)


class StatusService:
    @staticmethod
    def get_status(app_name: str, db: Session) -> StatusResponse:
        """
        Retrieves the status for the given application.

        - If an active record (status == "started") exists (build or unbuild),
          it returns that record's steps.
        - Otherwise, it returns the steps from the most recent record (build or unbuild).

        The response includes the record's uuid, application name, action, overall status, and a list of step details.
        """
        # Query for an active record with a status 'started' (either build or unbuild)
        active_record = (
            db.query(Application)
            .filter(
                Application.application_name == app_name,
                Application.status == "started"
            )
            .order_by(Application.timestamp.desc())
            .first()
        )

        if active_record:
            app_record = active_record
            logger.info("Active record found for '%s' (UUID: %s, action: %s).",
                        app_name, app_record.uuid, app_record.action)
        else:
            # No active record; retrieve the most recent record (build or unbuild)
            app_record = (
                db.query(Application)
                .filter(Application.application_name == app_name)
                .order_by(Application.timestamp.desc())
                .first()
            )
            if not app_record:
                logger.error("No record found for application '%s'.", app_name)
                return StatusResponse(
                    uuid="",
                    application_name=app_name,
                    action="",
                    status=BaseService.FAILED_STATE,
                    message=f"No record found for application '{app_name}'",
                    steps=[]
                )
            logger.info("No active record for '%s'. Using most recent record (UUID: %s, action: %s).",
                        app_name, app_record.uuid, app_record.action)

        # Retrieve all steps associated with the chosen record.
        steps_records = (
            db.query(Step)
            .filter(Step.uuid == app_record.uuid)
            .order_by(Step.timestamp)
            .all()
        )
        logger.debug("Found %d step(s) for record UUID: %s", len(steps_records), app_record.uuid)

        steps_info = []
        for step in steps_records:
            steps_info.append({
                "id": step.id,
                "task_name": step.task_name,
                "step_name": step.step_name,
                "status": step.status,
                "timestamp": step.timestamp.isoformat() if step.timestamp else None,
                "uuid": step.uuid
            })

        response = StatusResponse(
            uuid=str(app_record.uuid),
            application_name=str(app_record.application_name),
            action=str(app_record.action),
            status=str(app_record.status),
            message=str(app_record.status),
            steps=steps_info
        )
        logger.debug("Status response constructed: %s", response)
        return response
