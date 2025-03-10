import os
import subprocess
import yaml
from jinja2 import Environment, FileSystemLoader

class BuildService:
    TASKS_FOLDER = "tasks"
    RESOURCES_FOLDER = "resources"
    ENVIRONMENTS_FOLDER = "environments"

    def load_yaml(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        return {}

    def merge_envs(self, global_env, component_env):
        return {**global_env, **component_env}

    def render_template(self, template_path, context):
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        template = env.get_template(os.path.basename(template_path))
        return template.render(context)

    def load_config(self, task) -> dict:
        resource_name = task["resource"]
        environment_name = task["environment"]

        global_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, f"{environment_name}.yml")
        component_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, resource_name, f"{environment_name}.yml")

        global_env = self.load_yaml(global_env_path)
        component_env = self.load_yaml(component_env_path)
        merged_env = self.merge_envs(global_env, component_env)
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
            rendered_action_script = self.render_template(action_script_template_path, envs)
            with open(rendered_action_script_path, "w") as f:
                f.write(rendered_action_script)
            os.chmod(rendered_action_script_path, 0o755)

        print("rendered_action_script_path: ", rendered_action_script_path)

        if action_type != "shell":
            action_template = step["action_template"]
            action_template_name = action_template + ".j2"
            action_template_path = os.path.join(resource_path, action_template_name)
            rendered_action_template_path = os.path.join(resource_path, action_template)

            if os.path.exists(action_template_path):
                rendered_template = self.render_template(action_template_path, envs)
                print("rendered_template_path: ", rendered_action_template_path)
                with open(rendered_action_template_path, "w") as f:
                    f.write(rendered_template)

        self.call_subprocess(resource_name, rendered_action_script_path)
        return results

    def call_subprocess(self, resource_name, script_path) -> dict:
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

    def execute_task(self, task) -> dict:

        results = []

        task_name = task["name"]
        resource_name = task["resource"]
        environment_name = task["environment"]
        group_name = task["group"]
        type_name = task["type"]
        account_name = task["account"]
        configuration = task["configuration"]
        steps = task["steps"]

        print("================")
        print(task_name )
        print(resource_name )
        print(environment_name )
        print(group_name )
        print(type_name )
        print(account_name )
        print(configuration )
        print(steps )

        merged_env = self.load_config(task)

        for step in steps:
            print("----------")
            print(step["name"])
            result = self.run_step(resource_name, step, merged_env)
            results.append(result)

        return results

    def build(self, component: str) -> dict:
        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")

        tasks = self.load_yaml(yaml_path)

        if not tasks:
            return {"status": "error", "message": f"Task file {component}.yml not found", "component": component, "results": []}

        results = []

        for task in tasks:
            result = self.execute_task(task)


        return {"status": "success", "message": "Build process completed", "component": component, "results": results}

    def unbuild(self, component: str) -> dict:
        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")
        tasks = self.load_yaml(yaml_path)

        if not tasks:
            return {"status": "error", "message": f"Task file {component}.yml not found", "component": component, "results": []}

        results = []

        # for task in tasks:
            # resource_name = task["name"]
            # environment_name = task["environment"]
            # group_name = task["group"]
            # type_name = task["type"]
            # account_name = task["account"]
            # configuration = task["configuration"]
            # steps = task["steps"]
            #
            # resource_path = os.path.join(self.RESOURCES_FOLDER, resource_name)
            #
            # global_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, f"{environment_name}.yml")
            # component_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, resource_name, f"{environment_name}.yml")
            #
            # global_env = self.load_yaml(global_env_path)
            # component_env = self.load_yaml(component_env_path)
            # merged_env = self.merge_envs(global_env, component_env)
            #
            # destroy_template_path = os.path.join(resource_path, "destroy.sh.j2")
            # destroy_script_path = os.path.join(resource_path, "destroy.sh")
            #
            # if os.path.exists(destroy_template_path):
            #     rendered_destroy = self.render_template(destroy_template_path, merged_env)
            #     with open(destroy_script_path, "w") as f:
            #         f.write(rendered_destroy)
            #     os.chmod(destroy_script_path, 0o755)
            #
            # if os.path.exists(destroy_script_path):
            #     try:
            #         process = subprocess.run(["bash", destroy_script_path], capture_output=True, text=True)
            #         if process.returncode == 0:
            #             results.append({"resource": resource_name, "status": "success", "message": process.stdout})
            #         else:
            #             results.append({"resource": resource_name, "status": "error", "message": process.stderr})
            #     except Exception as e:
            #         results.append({"resource": resource_name, "status": "error", "message": str(e)})
            # else:
            #     results.append({"resource": resource_name, "status": "error", "message": "Destroy script not found"})

        return {"status": "success", "message": "Unbuild process completed", "component": component, "results": results}
