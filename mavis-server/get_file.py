import os
import secrets
import subprocess
import sys

import ecs


def register(subparsers):
    parser = subparsers.add_parser(
        "get-file",
        help="Download a file from an ECS container to local",
        description=(
            "Download a file from inside an ECS container to a local path, "
            "using S3 as an intermediary. The S3 object is always cleaned up."
        ),
    )
    parser.add_argument("env", help="Environment name (cluster will be mavis-ENV)")
    parser.add_argument("remote_path", help="Path of the file inside the container")
    parser.add_argument(
        "local_path",
        nargs="?",
        default=None,
        help="Local destination (file or directory). Defaults to current directory.",
    )
    parser.add_argument(
        "--task-id",
        dest="task_id",
        help="Task ID to target (auto-resolved for qa/production envs)",
    )
    parser.set_defaults(func=run)


def run(args):
    env = args.env

    ecs.confirm_production(env)
    ecs.ensure_authenticated()

    task_id = _resolve_task_id(env, args.task_id)
    bucket = ecs.s3_bucket(env)
    key = f"temp-{secrets.token_hex(8)}"
    s3_uri = f"s3://{bucket}/{key}"

    local_dest = _local_destination(args.remote_path, args.local_path)

    try:
        print(f"Uploading {args.remote_path} from task {task_id} to {s3_uri} ...")
        exit_code = ecs.run_command(
            env,
            task_id,
            f"aws s3 cp {args.remote_path} {s3_uri} --region {ecs.REGION}",
        )
        if exit_code != 0:
            sys.exit("Error: Failed to copy file from container to S3")

        print(f"Downloading from S3 to {local_dest} ...")
        download = subprocess.run(
            ["aws", "s3", "cp", s3_uri, local_dest, "--region", ecs.REGION]
        )
        if download.returncode != 0:
            sys.exit("Error: Failed to download file from S3")
    finally:
        subprocess.run(
            ["aws", "s3", "rm", s3_uri, "--region", ecs.REGION],
            capture_output=True,
        )

    print(f"File successfully downloaded to {local_dest}")


def _resolve_task_id(env, explicit_task_id):
    """Return a task ID, auto-resolving the service for known environments."""
    if explicit_task_id:
        task_id, _ = ecs.resolve_task(env, task_id=explicit_task_id)
        return task_id
    if env in ("qa", "production"):
        service = f"mavis-{env}-ops"
    elif env == "production-data-replication":
        service = "mavis-production-data-replication"
    else:
        sys.exit("Error: --task-id is required for this environment")
    task_id, _ = ecs.resolve_task(env, service=service)
    return task_id


def _local_destination(remote_path, local_path):
    """
    Resolve the local download destination.

    If local_path is given and is an existing directory, save as
    <local_path>/<basename of remote_path>. If local_path is a file path
    (or doesn't exist yet), use it as-is. Defaults to ./<basename>.
    """
    filename = os.path.basename(remote_path.rstrip("/"))
    if local_path is None:
        return os.path.join(".", filename)
    if os.path.isdir(local_path):
        return os.path.join(local_path, filename)
    return local_path
