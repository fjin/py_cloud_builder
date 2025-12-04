import unittest
from unittest.mock import MagicMock, patch
from services.unbuild_service import UnbuildService
from schemas import UnBuildResponse

class TestUnbuildService(unittest.TestCase):
    def setUp(self):
        self.service = UnbuildService()
        self.db = MagicMock()
        self.service.RESOURCES_FOLDER = "/tmp/resources"
        self.service.TEMPLATES_FOLDER = "/tmp/templates"
        self.service.DESTROY_CFN_SCRIPT = "destroy_cfn"
        self.service.DESTROY_TERRAFORM_SCRIPT = "destroy_terraform"
        self.service.CUSTOM_DESTROY_SCRIPT = "destroy.sh"

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("os.chmod")
    def test_destroy_task_cloudformation(self, mock_chmod, mock_open, mock_exists):
        mock_exists.return_value = True
        self.service.render_template = MagicMock(return_value="script")
        self.service.call_subprocess = MagicMock(return_value={"status": "success"})
        self.service.update_status = MagicMock()
        step = {"type": "cloudformation"}
        envs = {"key": "val"}
        result = self.service.destroy_task("res1", step, envs, self.db, "uuid1")
        self.assertEqual(result["status"], "success")
        self.service.render_template.assert_called()
        self.service.call_subprocess.assert_called()
        self.service.update_status.assert_called()

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("os.chmod")
    def test_destroy_task_no_template(self, mock_chmod, mock_open, mock_exists):
        mock_exists.return_value = False
        self.service.render_template = MagicMock()
        self.service.call_subprocess = MagicMock(return_value={"status": "success"})
        self.service.update_status = MagicMock()
        step = {"type": "custom"}
        envs = {"key": "val"}
        result = self.service.destroy_task("res2", step, envs, self.db, "uuid2")
        self.assertEqual(result["status"], "success")
        self.service.render_template.assert_not_called()
        self.service.call_subprocess.assert_called()
        self.service.update_status.assert_called()

    def test_execute_task_success(self):
        self.service.load_config = MagicMock(return_value={"env": "val"})
        self.service.destroy_task = MagicMock(return_value={"status": "success", "resource": "res", "message": "destroyed"})
        self.service.flatten_list = MagicMock(side_effect=lambda x: x)
        task = {"type": "infrastructure", "resource": "res", "steps": [{"name": "step1"}], "name": "task1"}
        results = self.service.execute_task(task, self.db, "uuid3")
        self.assertEqual(results[0]["status"], "success")

    def test_execute_task_fail_env(self):
        self.service.load_config = MagicMock(return_value={})
        task = {"type": "infrastructure", "resource": "res", "steps": [{"name": "step1"}], "name": "task1"}
        results = self.service.execute_task(task, self.db, "uuid4")
        self.assertEqual(results, [])

    def test_execute_task_fail_step(self):
        self.service.load_config = MagicMock(return_value={"env": "val"})
        def fail_destroy(*args, **kwargs):
            raise Exception("fail")
        self.service.destroy_task = fail_destroy
        self.service.flatten_list = MagicMock(side_effect=lambda x: x)
        task = {"type": "infrastructure", "resource": "res", "steps": [{"name": "step1"}], "name": "task1"}
        results = self.service.execute_task(task, self.db, "uuid5")
        self.assertEqual(results, [])

    @patch("os.path.exists")
    def test_unbuild_task_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        response = self.service.unbuild("comp", "/tmp/task", True, self.db)
        self.assertIsInstance(response, UnBuildResponse)
        self.assertEqual(response.status, self.service.FAILED_STATE)

    @patch("os.path.exists")
    def test_unbuild_already_in_progress(self, mock_exists):
        mock_exists.return_value = True
        app = MagicMock()
        app.uuid = "uuid6"
        self.db.query().filter().first.return_value = app
        response = self.service.unbuild("comp", "/tmp/task", True, self.db)
        self.assertEqual(response.status, self.service.FAILED_STATE)
        self.assertEqual(response.uuid, "uuid6")

    @patch("os.path.exists")
    def test_unbuild_no_build_record(self, mock_exists):
        mock_exists.return_value = True
        self.db.query().filter().first.return_value = None
        self.db.query().filter().order_by().first.return_value = None
        response = self.service.unbuild("comp", "/tmp/task", True, self.db)
        self.assertEqual(response.status, self.service.FAILED_STATE)
        self.assertEqual(response.uuid, "")

    @patch("os.path.exists")
    @patch("services.unbuild_service.UnbuildService.load_yaml")
    def test_unbuild_task_yaml_not_found(self, mock_load_yaml, mock_exists):
        mock_exists.return_value = True
        self.db.query().filter().first.return_value = None
        app = MagicMock()
        app.uuid = "uuid7"
        self.db.query().filter().order_by().first.return_value = app
        mock_load_yaml.return_value = None
        self.service.update_application_record = MagicMock()
        response = self.service.unbuild("comp", "/tmp/task", True, self.db)
        self.assertEqual(response.status, self.service.FAILED_STATE)
        self.assertEqual(response.uuid, "uuid7")

    @patch("os.path.exists")
    @patch("services.unbuild_service.UnbuildService.load_yaml")
    def test_unbuild_success(self, mock_load_yaml, mock_exists):
        mock_exists.return_value = True
        self.db.query().filter().first.return_value = None
        app = MagicMock()
        app.uuid = "uuid8"
        self.db.query().filter().order_by().first.return_value = app
        mock_load_yaml.return_value = [{"type": "infrastructure", "resource": "res", "steps": [{"name": "step1"}], "name": "task1"}]
        self.service.update_application_record = MagicMock()
        self.service.delete_application_record = MagicMock()
        self.service.execute_task = MagicMock(return_value=[
            {"status": self.service.SUCCESS_STATE, "resource": "res", "message": "destroyed"}
        ])
        response = self.service.unbuild("comp", "/tmp/task", True, self.db)
        self.assertEqual(response.status, self.service.SUCCESS_STATE)
        self.service.delete_application_record.assert_called()

    @patch("os.path.exists")
    @patch("services.unbuild_service.UnbuildService.load_yaml")
    def test_unbuild_failed_step(self, mock_load_yaml, mock_exists):
        mock_exists.return_value = True
        self.db.query().filter().first.return_value = None
        app = MagicMock()
        app.uuid = "uuid9"
        self.db.query().filter().order_by().first.return_value = app
        mock_load_yaml.return_value = [{"type": "infrastructure", "resource": "res", "steps": [{"name": "step1"}], "name": "task1"}]
        self.service.update_application_record = MagicMock()
        self.service.delete_application_record = MagicMock()
        self.service.execute_task = MagicMock(return_value=[
            {"status": self.service.FAILED_STATE, "resource": "res", "message": "failed"}
        ])
        response = self.service.unbuild("comp", "/tmp/task", True, self.db)
        self.assertEqual(response.status, self.service.FAILED_STATE)
        self.service.delete_application_record.assert_not_called()

if __name__ == "__main__":
    unittest.main()
