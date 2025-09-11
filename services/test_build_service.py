import unittest
import os
import uuid
import logging
from datetime import datetime
from services.build_service import BuildService
from models import Application, Step

# Configure logger for testing (prints to console)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Dummy Query to simulate SQLAlchemy query results.
class DummyQuery:
    def __init__(self, data):
        self.data = data

    def filter(self, *args, **kwargs):
        # For testing, we ignore filter conditions and return self.
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.data[0] if self.data else None

    def all(self):
        return self.data

# DummyDB simulates a minimal DB session for testing.
class DummyDB:
    def __init__(self):
        self.applications = []
        self.steps = []
        self.commits = 0
        self.rollbacks = 0

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
        # Dummy refresh does nothing.
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

# DummyBuildService subclass to override file I/O and subprocess calls.
class DummyBuildService(BuildService):
    def render_template(self, template_path, context):
        # Instead of actual rendering, return a dummy string.
        return "rendered content"

    def call_subprocess(self, resource_name, script_path, build_id=None):
        # Simulate a successful subprocess call.
        return {"resource": resource_name, "status": "success", "message": "dummy output", "uuid": build_id}

    def load_yaml(self, file_path):
        # If file_path indicates an environments file, return a dictionary.
        if self.ENVIRONMENTS_FOLDER in file_path:
            return {"dummy_key": "dummy_value"}
        # Otherwise, assume it's the tasks file and return a dummy tasks list.
        return [
            {
                "name": "task1",
                "resource": "res1",
                "environment": "np",
                "steps": [
                    {"name": "step1", "action_script": "script.sh", "type": "shell"}
                ]
            },
            {
                "name": "task2",
                "resource": "res2",
                "environment": "np",
                "steps": [
                    {"name": "step1", "action_script": "script.sh", "type": "shell"}
                ]
            }
        ]

class TestBuildService(unittest.TestCase):
    def setUp(self):
        self.service = DummyBuildService()
        self.db = DummyDB()
        # Set folder paths to dummy values.
        self.service.TASKS_FOLDER = "/dummy/tasks"
        self.service.RESOURCES_FOLDER = "/dummy/resources"
        self.service.ENVIRONMENTS_FOLDER = "/dummy/env"

    def test_execute_task(self):
        # Create a dummy task with two steps.
        task = {
            "name": "task1",
            "resource": "res1",
            "environment": "np",
            "steps": [
                {"name": "step1", "action_script": "script.sh", "type": "shell"},
                {"name": "step2", "action_script": "script.sh", "type": "shell"}
            ]
        }
        build_id = "dummy-build-id"
        results = self.service.execute_task(task, "build", self.db, build_id)
        self.assertIsInstance(results, list)
        # Expect two results, one per step.
        self.assertEqual(len(results), 2)
        for res in results:
            self.assertEqual(res.get("status"), "success")
            self.assertEqual(res.get("uuid"), build_id)

    def test_build_no_active_build(self):
        component = "test-infra"
        # For testing, our DummyBuildService.load_yaml returns two tasks.
        result = self.service.build(component, self.db)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["component"], component)
        self.assertIn("uuid", result)
        # Expect results list to be non-empty.
        self.assertTrue(len(result["results"]) > 0)
        # Check that an Application record was created.
        self.assertEqual(len(self.db.applications), 1)
        app = self.db.applications[0]
        self.assertEqual(app.application_name, component)
        self.assertEqual(app.status, "success")
        # Our dummy tasks list contains tasks named "task1" and "task2".
        self.assertEqual(set(app.tasks_built), {"task1", "task2"})

    def test_build_with_active_build(self):
        component = "test-infra"
        # Simulate an active build in the dummy DB.
        active_app = Application()
        active_app.uuid = "active-uuid"
        active_app.application_name = component
        active_app.status = "started"
        self.db.applications.append(active_app)
        result = self.service.build(component, self.db)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["uuid"], "active-uuid")
        self.assertEqual(result["message"], f"Build for component '{component}' is already in progress.")

if __name__ == "__main__":
    unittest.main()
