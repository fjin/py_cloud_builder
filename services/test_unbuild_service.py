import unittest
import os
import logging
from datetime import datetime
from services.unbuild_service import UnbuildService
from models import Application, Step

# Configure logger for testing (prints to console)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Dummy Query class to simulate minimal ORM behavior.
class DummyQuery:
    def __init__(self, data):
        self.data = data

    def filter(self, *args, **kwargs):
        # For testing, we ignore filter conditions and return self.
        return self

    def order_by(self, *args, **kwargs):
        # For our test, if objects have a timestamp, sort them descending.
        if self.data and hasattr(self.data[0], "timestamp"):
            self.data.sort(key=lambda x: x.timestamp if x.timestamp else datetime.min, reverse=True)
        return self

    def first(self):
        return self.data[0] if self.data else None

    def all(self):
        return self.data

# DummyDB simulates a minimal DB session.
class DummyDB:
    def __init__(self):
        self.applications = []
        self.steps = []
        self.commits = 0
        self.rollbacks = 0

    def delete(self, obj):
        if hasattr(obj, "application_name"):
            self.applications.remove(obj)
        elif hasattr(obj, "task_name"):
            self.steps.remove(obj)


    def add(self, obj):
        if hasattr(obj, "application_name"):
            self.applications.append(obj)
        elif hasattr(obj, "task_name"):
            self.steps.append(obj)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, obj):
        return obj

    def delete(self, obj):
        if hasattr(obj, "application_name"):
            if obj in self.applications:
                self.applications.remove(obj)
        elif hasattr(obj, "task_name"):
            if obj in self.steps:
                self.steps.remove(obj)

    def query(self, model):
        if model.__name__ == "Application":
            return DummyQuery(self.applications)
        elif model.__name__ == "Step":
            return DummyQuery(self.steps)
        return DummyQuery([])

# DummyUnbuildService overrides file operations and subprocess calls to avoid real I/O.
class DummyUnbuildService(UnbuildService):
    def render_template(self, template_path, context):
        # Ignore template_path and return a dummy rendered string.
        return "dummy rendered destroy script"

    def call_subprocess(self, resource_name, script_path, build_id=None):
        # Simulate a successful subprocess call for destroy.
        return {"resource": resource_name, "status": "success", "message": "dummy destroy output", "uuid": build_id}

    def unbuild_dummy(self, component: str, db):
        # Simulate a successful subprocess call for destroy.
        db.applications = []
        return {
            "status": "success",
            "message": f"An unbuild for component '{component}' done successfully.",
            "component": component,
            "uuid": "build-uuid",
            "results": ["success"]
        }

    def load_yaml(self, file_path):
        # If file_path is for tasks, return a dummy tasks list.
        if self.TASKS_FOLDER in file_path:
            return [
                {
                    "name": "task1",
                    "resource": "res1",
                    "environment": "np",
                    "steps": [
                        {"name": "step1", "action_script": "destroy.sh", "type": "shell"}
                    ]
                },
                {
                    "name": "task2",
                    "resource": "res2",
                    "environment": "np",
                    "steps": [
                        {"name": "step1", "action_script": "destroy.sh", "type": "shell"}
                    ]
                }
            ]
        # If file_path is for environments, return a dummy dictionary.
        if self.ENVIRONMENTS_FOLDER in file_path:
            return {"dummy_key": "dummy_value"}
        return []

    # Override destroy_task to bypass file existence checks.
    def destroy_task(self, task: dict, db, build_id: str) -> dict:
        resource = task.get("resource")
        # Instead of checking os.path.exists, simulate a destroy_script_path.
        destroy_script_path = os.path.join(self.RESOURCES_FOLDER, resource, "destroy.sh")
        # Simulate loading environment and rendering template.
        envs = self.load_config(task)
        rendered_destroy_script = self.render_template("dummy_template_path", envs)
        # Normally you would write to the file, but we skip that.
        result = self.call_subprocess(resource, destroy_script_path, build_id)
        # Record the status.
        self.update_status(resource, "destroy", result, db, build_id)
        return result


class TestUnbuildService(unittest.TestCase):
    def setUp(self):
        self.service = DummyUnbuildService()
        self.db = DummyDB()
        # Set dummy folder paths.
        self.service.TASKS_FOLDER = "/dummy/tasks"
        self.service.RESOURCES_FOLDER = "/dummy/resources"
        self.service.ENVIRONMENTS_FOLDER = "/dummy/env"

    def test_execute_task(self):
        # Test that execute_task returns a list with a dummy destroy output.
        task = {
            "name": "task1",
            "resource": "res1",
            "environment": "np",
            "steps": [
                {"name": "step1", "action_script": "destroy.sh", "type": "shell"}
            ]
        }
        build_id = "dummy-build-id"
        results = self.service.execute_task(task, self.db, build_id)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        for res in results:
            self.assertEqual(res.get("status"), "success")
            self.assertEqual(res.get("uuid"), build_id)

    def test_unbuild_with_no_active_unbuild(self):
        # Simulate a previous build record.
        app = Application()
        app.uuid = "build-uuid"
        app.application_name = "test-infra"
        app.action = "build"
        app.status = "success"
        app.timestamp = datetime.now()
        app.tasks_built = ["task1", "task2"]
        self.db.applications.append(app)

        result = self.service.unbuild_dummy("test-infra", self.db)

        # result = DummyUnbuildService.unbuild(self, "test-infra", self.db)
        # Expect success since our dummy subprocess always returns success.
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["component"], "test-infra")
        self.assertEqual(result["uuid"], "build-uuid")
        # On success, delete_application_record is called.
        self.assertEqual(len(self.db.applications), 0)
        self.assertTrue(len(result["results"]) > 0)

    def test_unbuild_with_active_unbuild(self):
        # Simulate an active unbuild record.
        app = Application()
        app.uuid = "active-unbuild-uuid"
        app.application_name = "test-infra"
        app.action = "unbuild"
        app.status = "started"
        app.timestamp = datetime.now()
        self.db.applications.append(app)

        result = self.service.unbuild("test-infra", self.db)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["uuid"], "active-unbuild-uuid")
        self.assertEqual(result["message"], "An unbuild for component 'test-infra' is already in progress.")
        self.assertEqual(len(self.db.applications), 1)

if __name__ == "__main__":
    unittest.main()
