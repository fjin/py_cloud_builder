import unittest
import tempfile
import os
import yaml
import logging
from datetime import datetime
from services.base_service import BaseService
from models import Step, Application

# Configure logger for testing (prints to console)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Dummy Query class to simulate minimal ORM behavior.
class DummyQuery:
    def __init__(self, data):
        self.data = data

    def filter(self, *args, **kwargs):
        # For simplicity, ignore filter conditions and return self.
        return self

    def order_by(self, *args, **kwargs):
        # For testing, simply return self.
        return self

    def first(self):
        return self.data[0] if self.data else None

    def all(self):
        return self.data

# Updated DummyDB with refresh() and delete() methods.
class DummyDB:
    def __init__(self):
        self.steps = []
        self.applications = []
        self.commits = 0
        self.rolled_back = 0

    def add(self, obj):
        if hasattr(obj, "task_name"):
            self.steps.append(obj)
        elif hasattr(obj, "application_name"):
            self.applications.append(obj)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rolled_back += 1

    def refresh(self, obj):
        # For our dummy DB, refresh does nothing.
        return obj

    def delete(self, obj):
        if hasattr(obj, "application_name"):
            if obj in self.applications:
                self.applications.remove(obj)
        elif hasattr(obj, "task_name"):
            if obj in self.steps:
                self.steps.remove(obj)

    def query(self, model):
        if model.__name__ == "Step":
            return DummyQuery(self.steps)
        elif model.__name__ == "Application":
            return DummyQuery(self.applications)
        return DummyQuery([])

# Dummy models for testing purposes (if needed)
# Assuming your models already exist in models.py; if not, create minimal versions.
# Here we assume Application and Step are SQLAlchemy-like objects with the attributes used in BaseService.

class TestBaseService(unittest.TestCase):
    def setUp(self):
        self.bs = BaseService()

    def test_flatten_list(self):
        nested = [1, [2, [3, 4], 5]]
        expected = [1, 2, 3, 4, 5]
        self.assertEqual(BaseService.flatten_list(nested), expected)

    def test_load_yaml_success(self):
        data = {'key': 'value'}
        with tempfile.NamedTemporaryFile('w+', delete=False) as tf:
            yaml.dump(data, tf)
            tf_path = tf.name
        result = BaseService.load_yaml(tf_path)
        os.unlink(tf_path)
        self.assertEqual(result, data)

    def test_load_yaml_nonexistent(self):
        result = BaseService.load_yaml("nonexistent.yml")
        self.assertEqual(result, {})

    def test_merge_envs(self):
        global_env = {'a': 1, 'b': 2}
        component_env = {'b': 3, 'c': 4}
        expected = {'a': 1, 'b': 3, 'c': 4}
        self.assertEqual(BaseService.merge_envs(global_env, component_env), expected)

    def test_render_template(self):
        template_content = "Hello, {{ name }}!"
        with tempfile.NamedTemporaryFile('w+', suffix=".j2", delete=False) as tf:
            tf.write(template_content)
            tf_path = tf.name
        context = {"name": "World"}
        result = BaseService.render_template(tf_path, context)
        os.unlink(tf_path)
        self.assertEqual(result, "Hello, World!")

    def test_call_subprocess_success(self):
        # Create a temporary bash script that echoes "hello"
        script_content = "#!/bin/bash\necho hello"
        with tempfile.NamedTemporaryFile('w+', delete=False) as tf:
            tf.write(script_content)
            script_path = tf.name
        os.chmod(script_path, 0o755)
        result = BaseService.call_subprocess("test_resource", script_path, "dummy-uuid")
        os.unlink(script_path)
        self.assertEqual(result.get("status"), "success")
        self.assertIn("hello", result.get("message"))
        self.assertEqual(result.get("uuid"), "dummy-uuid")

    def test_update_status(self):
        db = DummyDB()
        BaseService.update_status("res1", "step1", {"result": "ok"}, db, "dummy-uuid")
        self.assertEqual(len(db.steps), 1)
        step = db.steps[0]
        self.assertEqual(step.task_name, "res1")
        self.assertEqual(step.step_name, "step1")
        self.assertEqual(step.status, {"result": "ok"})
        self.assertEqual(step.uuid, "dummy-uuid")
        self.assertIsInstance(step.timestamp, datetime)

    def test_update_application_record(self):
        db = DummyDB()
        # Create a dummy Application object.
        app = Application()
        app.uuid = "dummy-uuid"
        app.application_name = "test-app"
        app.action = "build"
        app.status = "started"
        app.tasks_built = None
        db.applications.append(app)
        updated = BaseService.update_application_record(db, "dummy-uuid", status="success", tasks_built=["task1"])
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "success")
        self.assertEqual(updated.tasks_built, ["task1"])

    def test_delete_application_record(self):
        db = DummyDB()
        app = Application()
        app.uuid = "dummy-uuid"
        app.application_name = "test-app"
        app.action = "build"
        app.status = "started"
        db.applications.append(app)
        BaseService.delete_application_record(db, "dummy-uuid")
        self.assertEqual(len(db.applications), 0)

    def test_load_config(self):
        # Create temporary YAML files to simulate global and component environment files.
        global_data = {'var': 'global'}
        component_data = {'var': 'component'}
        with tempfile.NamedTemporaryFile('w+', delete=False) as tf1:
            yaml.dump(global_data, tf1)
            global_path = tf1.name
        with tempfile.NamedTemporaryFile('w+', delete=False) as tf2:
            yaml.dump(component_data, tf2)
            comp_path = tf2.name

        # Simulate file structure by placing files in a temporary directory.
        temp_dir = tempfile.mkdtemp()
        global_dir = os.path.join(temp_dir, "np")
        comp_dir = os.path.join(temp_dir, "comp")
        os.mkdir(global_dir)
        os.mkdir(comp_dir)
        global_file = os.path.join(global_dir, "np.yml")
        comp_file = os.path.join(comp_dir, "np.yml")
        os.rename(global_path, global_file)
        os.rename(comp_path, comp_file)

        # Override the ENVIRONMENTS_FOLDER in our BaseService instance.
        self.bs.ENVIRONMENTS_FOLDER = temp_dir

        task = {"resource": "comp", "environment": "np"}
        config = self.bs.load_config(task)
        # Expected: component env overrides global env.
        expected = {"var": "component"}
        self.assertEqual(config, expected)

        # Cleanup temporary files and directories.
        os.remove(global_file)
        os.remove(comp_file)
        os.rmdir(global_dir)
        os.rmdir(comp_dir)
        os.rmdir(temp_dir)

if __name__ == "__main__":
    unittest.main()
