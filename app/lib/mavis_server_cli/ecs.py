import json
import subprocess
import sys

REGION = "eu-west-2"
PRODUCTION_ENVS = {"production", "production-data-replication"}


def cluster(env):
    return f"mavis-{env}"


def s3_bucket(env):
    if env in PRODUCTION_ENVS:
        return "mavis-filetransfer-production"
    return "mavis-filetransfer-development"


def ensure_authenticated(exit_without_login=False):
    """Check AWS auth; attempt SSO login if needed."""
    result = subprocess.run(
        ["aws", "sts", "get-caller-identity"],
        capture_output=True,
    )
    if result.returncode == 0:
        return
    if exit_without_login:
        sys.exit(
            "Error: Not authenticated with AWS. "
            "Run 'aws sso login' and try again."
        )
    print("Not authenticated with AWS. Attempting SSO login...")
    login = subprocess.run(["aws", "sso", "login"])
    if login.returncode != 0:
        sys.exit("Error: AWS SSO login failed.")
    recheck = subprocess.run(
        ["aws", "sts", "get-caller-identity"],
        capture_output=True,
    )
    if recheck.returncode != 0:
        sys.exit("Error: Still not authenticated after SSO login.")


def confirm_production(env):
    """Prompt for confirmation before operating on production."""
    if env != "production":
        return
    print("Warning: You are about to operate on PRODUCTION (not data-replication).")
    answer = input("Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        sys.exit("Aborted.")


def aws_json(*cmd):
    """Run an AWS CLI command and return parsed JSON output."""
    result = subprocess.run(["aws", *cmd], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Error running 'aws {' '.join(cmd)}':\n{result.stderr.strip()}")
    return json.loads(result.stdout)


def resolve_task(env, task_id=None, task_ip=None, service=None):
    """
    Resolve a task to (short_task_id, container_name).

    container_name is the name of the running 'application' container.
    Returns None for container_name if no such container is found — callers
    that require it (e.g. shell) should check and error accordingly.
    """
    cl = cluster(env)

    if task_id:
        data = aws_json(
            "ecs", "describe-tasks",
            "--region", REGION,
            "--cluster", cl,
            "--tasks", task_id,
        )
        tasks = data.get("tasks", [])
        if not tasks:
            sys.exit(f"Error: Task {task_id} not found in cluster {cl}")
        task = tasks[0]
        if task["lastStatus"] != "RUNNING":
            sys.exit(
                f"Error: Task {task_id} is not running "
                f"(status: {task['lastStatus']})"
            )
        return task_id, _application_container(task)

    # Discover running tasks (optionally filtered by service)
    list_cmd = [
        "ecs", "list-tasks",
        "--region", REGION,
        "--cluster", cl,
        "--desired-status", "RUNNING",
    ]
    if service:
        list_cmd += ["--service-name", service]

    task_arns = aws_json(*list_cmd).get("taskArns", [])
    if not task_arns:
        svc = f" for service {service}" if service else ""
        sys.exit(f"Error: No running tasks found in cluster {cl}{svc}")

    tasks = aws_json(
        "ecs", "describe-tasks",
        "--region", REGION,
        "--cluster", cl,
        "--tasks", *task_arns,
    ).get("tasks", [])

    if task_ip:
        for task in tasks:
            if _task_private_ip(task) == task_ip:
                return _short_id(task), _application_container(task)
        svc = f" for service {service}" if service else ""
        sys.exit(
            f"Error: No running task found with IP {task_ip} "
            f"in cluster {cl}{svc}"
        )

    # Pick the first task that has a running application container
    for task in tasks:
        container = _application_container(task)
        if container:
            return _short_id(task), container

    svc = f" for service {service}" if service else ""
    sys.exit(
        f"Error: No running tasks with a running 'application' container "
        f"found in cluster {cl}{svc}"
    )


def run_command(env, task_id, command, container=None, interactive=True):
    """Execute a command in an ECS task, returning the exit code."""
    cmd = [
        "aws", "ecs", "execute-command",
        "--region", REGION,
        "--cluster", cluster(env),
        "--task", task_id,
        "--command", command,
    ]
    if container:
        cmd += ["--container", container]
    if interactive:
        cmd.append("--interactive")
    return subprocess.run(cmd).returncode


# --- private helpers ---

def _short_id(task):
    return task["taskArn"].split("/")[-1]


def _application_container(task):
    for c in task.get("containers", []):
        if (
            c.get("name") == "application"
            and c.get("lastStatus") == "RUNNING"
            and c.get("runtimeId")
        ):
            return c["name"]
    return None


def _task_private_ip(task):
    for attachment in task.get("attachments", []):
        for detail in attachment.get("details", []):
            if detail.get("name") == "privateIPv4Address":
                return detail.get("value")
    return None
