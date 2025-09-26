import unittest
from unittest.mock import patch, MagicMock
from services.environment_service import EnvironmentService
from schemas import EnvironmentResponse

class TestEnvironmentService(unittest.TestCase):
    def setUp(self):
        self.service = EnvironmentService()
        self.service.ENVIRONMENTS_FOLDER = "envs"
        self.service.RESOURCES_FOLDER = "resources"
        self.service.TASKS_FOLDER = "tasks"

    @patch.object(EnvironmentService, 'load_yaml')
    @patch.object(EnvironmentService, 'load_config')
    @patch.object(EnvironmentService, 'render_and_merge_envs')
    def test_get_environment_success(self, mock_merge, mock_config, mock_yaml):
        mock_yaml.return_value = [
            {"resource": "res1", "steps": [{"use_template": True, "action_config": "cfg.yml"}]}
        ]
        mock_config.return_value = {"VAR": "value"}
        mock_merge.return_value = {"VAR": "value", "TEMPLATE": "merged"}

        with patch("logging.Logger.debug") as mock_log:
            resp = self.service.get_environment("comp", "env_path", "res_path", "task_path")
            self.assertIsInstance(resp, EnvironmentResponse)
            self.assertEqual(resp.status, "success")
            self.assertEqual(resp.component, "comp")
            self.assertIn("VAR", resp.environment)
            mock_log.assert_called()

    @patch.object(EnvironmentService, 'load_yaml')
    def test_get_environment_missing_task_file(self, mock_yaml):
        mock_yaml.return_value = None
        resp = self.service.get_environment("comp", "env_path", "res_path", "task_path")
        self.assertIsInstance(resp, EnvironmentResponse)
        self.assertEqual(resp.status, self.service.FAILED_STATE)
        self.assertEqual(resp.environment, {})
        self.assertIn("not found", resp.message)

if __name__ == "__main__":
    unittest.main()
