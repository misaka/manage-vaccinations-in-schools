import sys

from mavis_server import ecs


def register(subparsers):
    parser = subparsers.add_parser(
        "shell",
        help="Open an interactive shell in an ECS container",
        description="Open an interactive bash shell in an ECS container.",
    )
    parser.add_argument("env", help="Environment name (cluster will be mavis-ENV)")
    parser.add_argument("--service", help="Override the ECS service name")
    parser.add_argument(
        "--task-id", dest="task_id", help="Connect to a specific task by ID"
    )
    parser.add_argument(
        "--task-ip",
        dest="task_ip",
        help="Connect to a task by its private IPv4 address",
    )
    parser.add_argument(
        "-x",
        "--exit-without-login",
        dest="exit_without_login",
        action="store_true",
        help="Exit instead of prompting for AWS SSO login",
    )
    parser.set_defaults(func=run)


def run(args):
    env = args.env

    ecs.confirm_production(env)
    ecs.ensure_authenticated(exit_without_login=args.exit_without_login)

    task_id, container = ecs.resolve_task(
        env,
        task_id=args.task_id,
        task_ip=args.task_ip,
        service=args.service,
    )

    if not container:
        sys.exit(f"Error: No running 'application' container found in task {task_id}")

    print(
        f"Opening shell in task {task_id}"
        + (f" (service {service})" if service else "")
    )
    exit_code = ecs.run_command(
        env, task_id, "/rails/bin/docker-entrypoint /bin/bash", container=container
    )

    sys.exit(exit_code)
