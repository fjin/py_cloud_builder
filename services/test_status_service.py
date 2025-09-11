import unittest
import logging
from datetime import datetime
from services.status_service import StatusService, get_status
from models import Application, Step

# Configure logger for testing (prints to console)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# DummyQuery simulates a minimal SQLAlchemy query.
class DummyQuery:
    def __init__(self, data):
        self.data = data

    def filter(self, *args, **kwargs):
        # For testing, we ignore filter conditions and return self.
        return self

    def order_by(self, *args, **kwargs):
        # If objects have a timestamp, sort them descending (for Application) or ascending (for Step)
        if self.data and hasattr(self.data[0], "timestamp"):
            # Check if ordering by descending: we assume the caller uses reverse=True for Application
            # Here, we'll sort descending by default.
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

    def add(self, obj):
        if hasattr(obj, "application_name"):
            self.applications.append(obj)
        elif hasattr(obj, "task_name"):
            self.steps.append(obj)

    def commit(self):
        pass  # No-op for testing.

    def rollback(self):
        pass  # No-op for testing.

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

class TestStatusService(unittest.TestCase):
    def setUp(self):
        self.status_service = StatusService()
        self.db = DummyDB()

    def test_get_status_no_record(self):
        # When no Application record exists, get_status should return an error.
        result = get_status("nonexistent-app", self.db)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "No record found for nonexistent-app")

    def test_get_status_active_record(self):
        # Create an active Application record.
        app = Application()
        app.uuid = "active-uuid"
        app.application_name = "test-app"
        app.action = "build"
        app.status = "started"
        app.timestamp = datetime(2025, 3, 15, 10, 0, 0)
        self.db.applications.append(app)
        # Create one Step associated with this Application record.
        step1 = Step()
        step1.id = 1
        step1.task_name = "task1"
        step1.step_name = "step1"
        step1.status = {"result": "success"}
        step1.timestamp = datetime(2025, 3, 15, 10, 1, 0)
        step1.uuid = "active-uuid"
        self.db.steps.append(step1)
        result = get_status("test-app", self.db)
        # Verify that the active record is used.
        self.assertEqual(result["uuid"], "active-uuid")
        self.assertEqual(result["application_name"], "test-app")
        self.assertEqual(result["action"], "build")
        self.assertEqual(result["status"], "started")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["task_name"], "task1")
        self.assertEqual(result["steps"][0]["step_name"], "step1")

    def test_get_status_most_recent_record(self):
        # Create an Application record that is not active (status != "started").
        app = Application()
        app.uuid = "old-uuid"
        app.application_name = "test-app"
        app.action = "build"
        app.status = "success"
        app.timestamp = datetime(2025, 3, 15, 9, 0, 0)
        self.db.applications.append(app)
        # Create a Step associated with this record.
        step1 = Step()
        step1.id = 2
        step1.task_name = "task2"
        step1.step_name = "step1"
        step1.status = {"result": "success"}
        step1.timestamp = datetime(2025, 3, 15, 9, 5, 0)
        step1.uuid = "old-uuid"
        self.db.steps.append(step1)
        result = get_status("test-app", self.db)
        # Verify that the most recent record is used.
        self.assertEqual(result["uuid"], "old-uuid")
        self.assertEqual(result["application_name"], "test-app")
        self.assertEqual(result["action"], "build")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["task_name"], "task2")
        self.assertEqual(result["steps"][0]["step_name"], "step1")

if __name__ == "__main__":
    unittest.main()
