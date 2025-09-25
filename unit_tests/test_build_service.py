import unittest
from unittest.mock import MagicMock, patch
from services.build_service import BuildService
from models import Application
from schemas import BuildResponse

class TestBuildService(unittest.TestCase):
    def setUp(self):
        self.bs = BuildService()
        self.bs.ENVIRONMENTS_FOLDER = 'envs'
        self.bs.RESOURCES_FOLDER = 'resources'
        self.bs.TASKS_FOLDER = 'tasks'

    @patch('services.build_service.BuildService.render_template')
    @patch('services.build_service.BuildService.call_subprocess')
    @patch('services.build_service.BuildService.update_status')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('os.chmod')
    def test_run_step_cloudformation(self, mock_chmod, mock_open, mock_exists, mock_update_status, mock_call_subprocess, mock_render_template):
        mock_render_template.return_value = "#!/bin/bash\necho Hello"
        mock_call_subprocess.return_value = {"status": "success"}
        db = MagicMock()
        result = self.bs.run_step("myresource", {"type": "cloudformation"}, {}, db, "buildid")
        self.assertEqual(result["status"], "success")
        mock_update_status.assert_called()

    @patch('os.path.exists', return_value=False)
    def test_run_step_template_missing(self, mock_exists):
        db = MagicMock()
        with self.assertRaises(RuntimeError):
            self.bs.run_step("myresource", {"type": "cloudformation"}, {}, db, "buildid")

    @patch('services.build_service.BuildService.load_yaml')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_render_cloud_template_use_template(self, mock_open, mock_exists, mock_load_yaml):
        mock_load_yaml.return_value = {"key": "value"}
        self.bs.TEMPLATES_FOLDER = "templates"
        self.bs.render_template = MagicMock(return_value="rendered")
        self.bs.render_and_merge_envs = MagicMock(return_value={"merged": True})
        self.bs.render_cloud_template(True, "cloudformation", "type", "config.yml", "resource_path", "template", {})
        self.bs.render_template.assert_called()

    @patch('os.path.exists', return_value=False)
    def test_render_cloud_template_missing(self, mock_exists):
        with self.assertRaises(RuntimeError):
            self.bs.render_cloud_template(False, "cloudformation", "type", "config.yml", "resource_path", "template", {})

    @patch('services.build_service.BuildService.run_step')
    @patch('services.build_service.BuildService.load_config')
    def test_execute_task_success(self, mock_load_config, mock_run_step):
        mock_load_config.return_value = {"env": "val"}
        mock_run_step.return_value = {"status": "success"}
        db = MagicMock()
        task = {"name": "task1", "resource": "res1", "steps": [{"name": "step1"}]}
        result = self.bs.execute_task(task, "build", db, "buildid")
        self.assertTrue(any(r.get("status") == "success" for r in result))

    @patch('services.build_service.BuildService.load_config', return_value=None)
    def test_execute_task_no_env(self, mock_load_config):
        db = MagicMock()
        task = {"name": "task1", "resource": "res1", "steps": [{"name": "step1"}]}
        result = self.bs.execute_task(task, "build", db, "buildid")
        self.assertEqual(result, [])

    @patch('services.build_service.BuildService.run_step', side_effect=Exception("fail"))
    @patch('services.build_service.BuildService.load_config', return_value={"env": "val"})
    def test_execute_task_step_fail(self, mock_load_config, mock_run_step):
        db = MagicMock()
        task = {"name": "task1", "resource": "res1", "steps": [{"name": "step1"}]}
        result = self.bs.execute_task(task, "build", db, "buildid")
        self.assertEqual(result, [])

    @patch('services.build_service.BuildService.load_yaml')
    @patch('services.build_service.BuildService.execute_task')
    def test_build_success(self, mock_execute_task, mock_load_yaml):
        db = MagicMock()
        db.query().filter().first.return_value = None
        db.add = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()
        mock_load_yaml.return_value = [{"name": "task1", "resource": "res1", "steps": [{}]}]
        # Return all required fields for BuildResponse
        mock_execute_task.return_value = [{
            "status": self.bs.SUCCESS_STATE,
            "resource": "res1",
            "message": "step succeeded"
        }]
        response = self.bs.build("mycomponent", "/tmp/env", "/tmp/res", "/tmp/task", db)
        self.assertIsInstance(response, BuildResponse)
        self.assertEqual(response.status, self.bs.SUCCESS_STATE)

    @patch('services.build_service.BuildService.load_yaml', return_value=None)
    def test_build_no_task_file(self, mock_load_yaml):
        db = MagicMock()
        db.query().filter().first.return_value = None
        response = self.bs.build("mycomponent", "/tmp/env", "/tmp/res", "/tmp/task", db)
        self.assertEqual(response.status, self.bs.FAILED_STATE)

    def test_build_invalid_paths(self):
        db = MagicMock()
        with self.assertRaises(ValueError):
            self.bs.build("mycomponent", None, "/tmp/res", "/tmp/task", db)

if __name__ == '__main__':
    unittest.main()
