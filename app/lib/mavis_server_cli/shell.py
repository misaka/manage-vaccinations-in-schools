import sys

from app.lib.mavis_server_cli import ecs


def register(subparsers):
    parser = subparsers.add_parser(
        "shell",
        help="Open an interactive shell in an ECS container",
        description="Open an interactive bash shell in an ECS container.",
    )
    parser.add_argument("env", help="Environment name (cluster will be mavis-ENV)")
    parser.add_argument("--service", help="Override the ECS service name")
    parser.add_argument("--task-id", dest="task_id", help="Connect to a specific task by ID")
    parser.add_argument("--task-ip", dest="task_ip", help="Connect to a task by its private IPv4 address")
    parser.add_argument(
        "-x", "--exit-without-login",
        dest="exit_without_login",
        action="store_true",
        help="Exit instead of prompting for AWS SSO login",
    )
    parser.set_defaults(func=run)


def run(args):
    env = args.env

    ecs.confirm_production(env)
    ecs.ensure_authenticated(exit_without_login=args.exit_without_login)

    service = _resolve_service(env, args.service, args.task_id, args.task_ip)
    task_id, container = ecs.resolve_task(
        env,
        task_id=args.task_id,
        task_ip=args.task_ip,
        service=service,
    )

    if not container:
        sys.exit(
            f"Error: No running 'application' container found in task {task_id}"
        )

    print(f"Opening shell in task {task_id}" + (f" (service {service})" if service else ""))
    exit_code = ecs.run_command(env, task_id, "/rails/bin/docker-entrypoint /bin/bash", container=container)
    sys.exit(exit_code)


def _resolve_service(env, explicit_service, task_id, task_ip):
    """
    Determine which ECS service to filter tasks by.

    - If a service was given explicitly, use it.
    - If a specific task is targeted (by ID or IP), no service filter is needed.
    - For *-data-replication environments, list all tasks in the cluster.
    - Otherwise default to the ops service for qa/production, web for everything else.
    """
    if explicit_service:
        return explicit_service
    if task_id or task_ip:
        return None
    if env.endswith("data-replication"):
        return None
    if env in ("qa", "production"):
        return f"mavis-{env}-ops"
    return f"mavis-{env}-web"
