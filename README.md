Below is an updated **README.md** file that includes the `resources` and `environments` folders in the project structure:


# py_builder

py_builder is a Python-based infrastructure orchestration tool designed to provision and de-provision AWS resources using YAML task definitions, Jinja2 templating, and a modular service architecture. It supports building, unbuilding (destroying), and checking the status of AWS infrastructure deployments via FastAPI endpoints. Detailed step statuses are logged in a database using SQLAlchemy.

## Project Structure

```

py_builder/
├── models.py              # Database models for Application and Step records.
├── services/
│   ├── __init__.py
│   ├── base_service.py    # Common helper methods (YAML loading, templating, subprocess calls, etc.)
│   ├── build_service.py   # Build orchestration (provisioning AWS infra).
│   ├── unbuild_service.py # Unbuild orchestration (destroying AWS infra).
│   └── status_service.py  # Service to query the status of builds/unbuilds.
├── tasks/                 # YAML task definitions (e.g., test-infra.yml).
├── resources/             # Contains scripts and templates used by the build/unbuild processes.
├── environments/          # Contains YAML files with environment configurations.
├── Dockerfile             # Dockerfile for containerized deployment.
├── requirements.txt       # Python dependencies.
└── README.md              # Project overview and instructions.

```

## Features

- **YAML Task Definitions:**  
  Define tasks for AWS infrastructure (e.g., CloudFormation, EC2, S3) in YAML files (e.g., `tasks/test-infra.yml`).
  The repo doesn't include any task YAML configurations, but you can have your own in your repo, and copy env files to tasks folder.

- **Jinja2 Templating:**  
  Dynamically render build and destroy scripts using environment-specific YAML configurations stored in the `environments/` folder.
  The repo doesn't include any environment-specific YAML configurations, but you can have your own in your repo, and copy env files to environments folder.

- **Resource Scripts:**  
  Store resource-specific scripts and templates in the `resources/` folder, which are used during the build and unbuild processes.
  The repo doesn't include any AWS CloudFormation templates, but you can have your own in your repo, and copy template files to resource folder.
- 
- **Build & Unbuild Locking:**  
  Prevent concurrent builds or unbuilds on the same component by enforcing a build locker via the database.

- **Step Logging:**  
  Log detailed step statuses (including output and timestamps) in the database for tracking and troubleshooting.

- **FastAPI Endpoints:**  
  Expose RESTful endpoints to trigger build, unbuild, and status checks.

- **Docker Support:**  
  A Dockerfile is provided for containerized deployment. Mount your local AWS credentials (e.g., the `.aws` folder) into the container for AWS CLI/SSO integration.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/fjin/py_builder.git
   cd py_builder
   git checkout develop
   ```

2. **Install Dependencies:**

   It's recommended to use a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Database Setup:**

   Configure your database as needed. For local development, SQLite is a good option.
   
   You don't have to use database, we can bypass it by setting flag "db_flag": "False" in curl commands.
   
## Usage

### Running the API

Start the FastAPI application using Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

- **Build:**  
  `POST /build/`  
  Request Body:
  ```json
  {
    "component": "test-infra",
    "db_flag": "False"
  }
  ```
  Triggers the build process based on the tasks defined in `tasks/test-infra.yml`.
  By default, db_flag is set "True" if you do not specify it in the curl command.  

- **Unbuild:**  
  `POST /unbuild/`  
  Request Body:
  ```json
  {
    "component": "test-infra",
    "db_flag": "False"
  }
  ```
  Triggers the unbuild (destroy) process for the specified component. (Note: If unbuild is successful, `/status` may return "No record found" since the record is deleted.)
  By default, db_flag is set "True" if you do not specify it in the curl command.

- **Status:**  
  `GET /status/?application_name=test-infra`  
  Returns the current steps and overall status from the active build/unbuild, or the most recent record if no build is in progress.

## AWS CLI and Credentials

If you use AWS CLI or AWS SSO locally, mount your local `.aws` directory into the container:

```bash
docker run -d -p 8000:8000 -v ~/.aws:/root/.aws py_builder_image
```

## Writing Task Definitions
Task definitions are written in YAML and stored in the `tasks/` folder. Each task can include multiple steps, such as running AWS CLI commands, executing scripts, or applying CloudFormation templates.
Here is an example of a simple task definition (`tasks/test-infra.yml`):

```yaml
---
# tasks to create an AWS Stack contains S3 and EC2
- name: "s3-test"
  resource: "s3-test"
  group: "test"
  type: "infrastructure"
  account: "unison-np"
  environment: "np"
  configuration: "s3-test"
  steps:
    - name: "deploy cfn"
      type: "cloudformation"
      action_script: "deploy_cfn.sh"
      action_template: "cfn.yml"

- name: "ec2-test"
  resource: "ec2-test"
  group: "test"
  type: "infrastructure"
  account: "unison-np"
  environment: "np"
  configuration: "ec2-test"
  steps:
    - name: "deploy cfn"
      type: "cloudformation"
      action_script: "deploy_cfn.sh"
      action_template: "cfn.yml"
    - name: "show instance ip"
      type: "shell"
      action_script: "showip.sh"


```

## Writing Environment Configurations
Environment-specific configurations are stored in the `environments/` folder as YAML files. These configurations can include parameters such as AWS region, instance types, and other settings that can be referenced in task definitions.
Here is an example of an environment configuration (`environments/np.yml`): 
```yaml
aws_region: "ap-southeast-2"

hosted_zone_id: "Z000000000000000001"
hosted_zone_name: "xxx.aws.123.com.au"

tooling_vpc_id: "vpc-0000000000123456"
tooling_subnet_1: "subnet-0000000000123456"
tooling_subnet_2: "subnet-0000000000223456"
tooling_subnet_3: "subnet-0000000000323456"
tooling_vpc_cidr: "10.99.99.99/24"
```

Project specific environment configurations can be created as needed. In folder named as component name, e.g. `environments/ec2-test/np.yml`.


## Docker

A Dockerfile is provided for containerized deployment.

1. **Build the Docker image:**

   ```bash
   docker build -t py_builder_image .
   ```

2. **Run the Container:**

   ```bash
   docker run -d -p 8000:8000 -v ~/.aws:/root/.aws py_builder_image
   ```

## Testing

Tests are written using Python’s built-in `unittest` framework and are located in the `services/` folder (e.g., `test_build_service.py`, `test_unbuild_service.py`, `test_status_service.py`).

To run all tests from the project root:

```bash
python -m unittest discover -s unit_tests
```

### Checking Test Coverage

1. **Install Coverage:**

   ```bash
   pip install coverage
   ```

2. **Run Tests with Coverage:**

   ```bash
   coverage run -m unittest discover -s unit_tests
   ```

3. **Generate a Report:**

   ```bash
   coverage report
   coverage html
   ```
   Then open `htmlcov/index.html` in your browser to review the coverage details.

## Contributing

Contributions are welcome! Fork the repository and submit pull requests with your improvements.

## License

This project is licensed under the MIT License.

## Contact

For questions or support, please open an issue on GitHub.
```

---

This version should render properly in GitHub. Adjust any sections as needed to best match your project's specifics.


## TODO list

### status check fails
### render_template throws error
### unbuild should follow a specific order