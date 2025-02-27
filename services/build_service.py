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

    def build(self, component: str) -> dict:
        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")
        tasks = self.load_yaml(yaml_path)

        if not tasks:
            return {"status": "error", "message": f"Task file {component}.yml not found", "component": component, "results": []}

        results = []

        for task in tasks:
            resource_name = task["name"]
            environment_name = task["environment"]
            resource_path = os.path.join(self.RESOURCES_FOLDER, resource_name)

            global_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, f"{environment_name}.yml")
            component_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, resource_name, f"{environment_name}.yml")

            global_env = self.load_yaml(global_env_path)
            component_env = self.load_yaml(component_env_path)
            merged_env = self.merge_envs(global_env, component_env)

            deploy_template_path = os.path.join(resource_path, "deploy.sh.j2")
            deploy_script_path = os.path.join(resource_path, "deploy.sh")

            if os.path.exists(deploy_template_path):
                rendered_deploy = self.render_template(deploy_template_path, merged_env)
                with open(deploy_script_path, "w") as f:
                    f.write(rendered_deploy)
                os.chmod(deploy_script_path, 0o755)

            cfn_template_path = os.path.join(resource_path, "cfn.yml.j2")
            cfn_rendered_path = os.path.join(resource_path, "cfn.yml")

            if os.path.exists(cfn_template_path):
                rendered_cfn = self.render_template(cfn_template_path, merged_env)
                with open(cfn_rendered_path, "w") as f:
                    f.write(rendered_cfn)

            if os.path.exists(deploy_script_path):
                try:
                    process = subprocess.run(["bash", deploy_script_path], capture_output=True, text=True)
                    if process.returncode == 0:
                        results.append({"resource": resource_name, "status": "success", "message": process.stdout})
                    else:
                        results.append({"resource": resource_name, "status": "error", "message": process.stderr})
                except Exception as e:
                    results.append({"resource": resource_name, "status": "error", "message": str(e)})

        return {"status": "success", "message": "Build process completed", "component": component, "results": results}

    def unbuild(self, component: str) -> dict:
        yaml_path = os.path.join(self.TASKS_FOLDER, f"{component}.yml")
        tasks = self.load_yaml(yaml_path)

        if not tasks:
            return {"status": "error", "message": f"Task file {component}.yml not found", "component": component, "results": []}

        results = []

        for task in tasks:
            resource_name = task["name"]
            environment_name = task["environment"]
            resource_path = os.path.join(self.RESOURCES_FOLDER, resource_name)

            global_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, f"{environment_name}.yml")
            component_env_path = os.path.join(self.ENVIRONMENTS_FOLDER, resource_name, f"{environment_name}.yml")

            global_env = self.load_yaml(global_env_path)
            component_env = self.load_yaml(component_env_path)
            merged_env = self.merge_envs(global_env, component_env)

            destroy_template_path = os.path.join(resource_path, "destroy.sh.j2")
            destroy_script_path = os.path.join(resource_path, "destroy.sh")

            if os.path.exists(destroy_template_path):
                rendered_destroy = self.render_template(destroy_template_path, merged_env)
                with open(destroy_script_path, "w") as f:
                    f.write(rendered_destroy)
                os.chmod(destroy_script_path, 0o755)

            if os.path.exists(destroy_script_path):
                try:
                    process = subprocess.run(["bash", destroy_script_path], capture_output=True, text=True)
                    if process.returncode == 0:
                        results.append({"resource": resource_name, "status": "success", "message": process.stdout})
                    else:
                        results.append({"resource": resource_name, "status": "error", "message": process.stderr})
                except Exception as e:
                    results.append({"resource": resource_name, "status": "error", "message": str(e)})
            else:
                results.append({"resource": resource_name, "status": "error", "message": "Destroy script not found"})

        return {"status": "success", "message": "Unbuild process completed", "component": component, "results": results}
