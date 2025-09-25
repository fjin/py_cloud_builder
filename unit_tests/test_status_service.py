import unittest
from unittest.mock import MagicMock
from services.status_service import StatusService
from schemas import StatusResponse

class TestStatusService(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()

    def test_get_status_active_record(self):
        active_app = MagicMock()
        active_app.uuid = "uuid1"
        active_app.application_name = "myapp"
        active_app.action = "build"
        active_app.status = "started"
        step = MagicMock()
        step.id = 1
        step.task_name = "task"
        step.step_name = "step"
        step.status = {"status": "success"}  # status as dict
        step.timestamp = None
        step.uuid = "uuid1"
        self.db.query().filter().order_by().first.side_effect = [active_app]
        self.db.query().filter().order_by().all.return_value = [step]
        response = StatusService.get_status("myapp", self.db)
        self.assertIsInstance(response, StatusResponse)
        self.assertEqual(response.uuid, "uuid1")
        self.assertEqual(response.application_name, "myapp")
        self.assertEqual(len(response.steps), 1)
        self.assertEqual(response.steps[0].step_name, "step")  # fixed

    def test_get_status_recent_record(self):
        recent_app = MagicMock()
        recent_app.uuid = "uuid2"
        recent_app.application_name = "myapp"
        recent_app.action = "unbuild"
        recent_app.status = "finished"
        step = MagicMock()
        step.id = 2
        step.task_name = "task2"
        step.step_name = "step2"
        step.status = {"status": "failed"}  # status as dict
        step.timestamp = None
        step.uuid = "uuid2"
        self.db.query().filter().order_by().first.side_effect = [None, recent_app]
        self.db.query().filter().order_by().all.return_value = [step]
        response = StatusService.get_status("myapp", self.db)
        self.assertEqual(response.uuid, "uuid2")
        self.assertEqual(response.action, "unbuild")
        self.assertEqual(response.status, "finished")
        self.assertEqual(len(response.steps), 1)
        self.assertEqual(response.steps[0].step_name, "step2")  # fixed

    def test_get_status_no_record(self):
        self.db.query().filter().order_by().first.side_effect = [None, None]
        response = StatusService.get_status("myapp", self.db)
        self.assertIsInstance(response, StatusResponse)
        self.assertEqual(response.uuid, "")
        self.assertEqual(response.status, "error")  # expect "error"
        self.assertEqual(response.steps, [])

if __name__ == '__main__':
    unittest.main()
