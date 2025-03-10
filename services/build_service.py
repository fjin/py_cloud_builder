import os
import subprocess
import yaml
from jinja2 import Environment, FileSystemLoader
import boto3
import botocore.exceptions

def flatten_list(nested_list):
    """Recursively flattens a nested list into a single-level list."""
    flat_list = []
    for element in nested_list:
        if isinstance(element, list):
            flat_list.extend(flatten_list(element))
        else:
            flat_list.append(element)
    return flat_list

def call_subprocess(resource_name, script_path) -> dict:
    results = []
    if os.path.exists(script_path):
        try:
            process = subprocess.run(["bash", script_path], capture_output=True, text=True)
            if process.returncode == 0:
                results.append({"resource": resource_name, "status": "success", "message": process.stdout})
            else:
                results.append({"resource": resource_name, "status": "error", "message": process.stderr})
        except Exception as e:
            print("error")
            results.append({"resource": resource_name, "status": "error", "message": str(e)})
    return results


def load_yaml(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    return {}


def merge_envs(global_env, component_env):
    return {**global_env, **component_env}


def render_template(template_path, context):
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
    template = env.get_template(os.path.basename(template_path))
    return template.render(context)


class BuildService:
    TASKS_FOLDER = "tasks"
    RESOURCES_FOLDER = "resources"
    ENVIRONMENTS_FOLDER = "environments"

    def load_config(self, task) -> dict:
        resource_name = task["resource"]
        environment_name = task["environment"]

        global_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, f"{environment_name}.yml")
        component_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, resource_name, f"{environment_name}.yml")

        global_env = load_yaml(global_env_path)
        component_env = load_yaml(component_env_path)
        merged_env = merge_envs(global_env, component_env)
        return merged_env

    def run_step(self, resource_name, step, envs) -> dict:
        results = []
        action_script = step["action_script"]
        action_type = step["type"]

        resource_path = os.path.join(self.RESOURCES_FOLDER, resource_name)

        action_script_template_name = action_script + ".j2"
        action_script_template_path = os.path.join(resource_path, action_script_template_name)
        rendered_action_script_path = os.path.join(resource_path, action_script)

        if os.path.exists(action_script_template_path):
            rendered_action_script = render_template(action_script_template_path, envs)
            with open(rendered_action_script_path, "w") as f:
                f.write(rendered_action_script)
            os.chmod(rendered_action_script_path, 0o755)

        if action_type != "shell":
            action_template = step["action_template"]
            action_template_name = action_template + ".j2"
            action_template_path = os.path.join(resource_path, action_template_name)
            rendered_action_template_path = os.path.join(resource_path, action_template)

            if os.path.exists(action_template_path):
                rendered_template = render_template(action_template_path, envs)
                with open(rendered_action_template_path, "w") as f:
                    f.write(rendered_template)

        result = call_subprocess(resource_name, rendered_action_script_path)
        results.append(result)
        return results

    def delete_stack(stack_name: str) -> dict:
        cf_client = boto3.client('cloudformation')
        try:
            response = cf_client.delete_stack(StackName=stack_name)
            print(f"Deletion initiated for stack: {stack_name}")
            return response
        except botocore.exceptions.ClientError as e:
            print(f"Error deleting stack {stack_name}: {e}")
            return None

    def wait_for_stack_deletion(stack_name: str) -> dict:
        cf_client = boto3.client('cloudformation')
        waiter = cf_client.get_waiter('stack_delete_complete')
        try:
            waiter.wait(StackName=stack_name)
            print(f"Stack {stack_name} deleted successfully.")
            return {"status": "success", "message": f"Stack {stack_name} deleted successfully.", "stack_name": {stack_name}, "results": ["Stack {stack_name} deleted successfully."]}
        except Exception as e:
            print(f"Error waiting for stack deletion: {e}")
            return {"status": "error", "message": f"Stack {stack_name} cannot be deleted successfully.", "stack_name": {stack_name}, "results": ["Stack {stack_name} cannot be deleted successfully."]}

    def destroy_task(self, task, envs) -> dict:
        results = []
        print("==============")
        print(task["name"], envs.get("stack_name"))
        result = self.delete_stack(self, envs.get("stack_name"))
        results.append(result)
        result = self.wait_for_stack_deletion(envs.get("stack_name"))
        results.append(result)

        return results


    def execute_task(self, task, action) -> dict:

        results = []

        task_name = task["name"]
        resource_name = task["resource"]
        environment_name = task["environment"]
        group_name = task["group"]
        type_name = task["type"]
        account_name = task["account"]
        configuration = task["configuration"]
        steps = task["steps"]

        print(f"task: {task_name} {resource_name} {environment_name} {group_name} {type_name} {account_name} {configuration} {steps}")

        merged_env = self.load_config(task)
        if action == "unbuild":
            return self.destroy_task(task, merged_env)

        for step in steps:
            result = self.run_step(resource_name, step, merged_env)
            results.append(result)

        return results

    def build(self, component: str) -> dict:
        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")

        tasks = load_yaml(yaml_path)

        if not tasks:
            return {"status": "error", "message": f"Task file {component}.yml not found", "component": component, "results": []}

        results = []

        for task in tasks:
            result = self.execute_task(task, "build")
            print(result)
            results.append(result)

        results = flatten_list(results)
        return {"status": "success", "message": "Build process completed", "component": component, "results": results}

    def unbuild(self, component: str) -> dict:
        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")
        tasks = load_yaml(yaml_path)

        if not tasks:
            return {"status": "error", "message": f"Task file {component}.yml not found", "component": component, "results": []}

        results = []

        for task in tasks:
            result = self.execute_task(task, "unbuild")
            results.append(result)

        results = flatten_list(results)
        return {"status": "success", "message": "Unbuild process completed", "component": component, "results": results}
