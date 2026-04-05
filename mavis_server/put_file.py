import os
import secrets
import subprocess
import sys

from mavis_server import ecs


def register(subparsers):
    parser = subparsers.add_parser(
        "put-file",
        help="Upload a local file to an ECS container",
        description=(
            "Upload a local file to a path inside an ECS container, "
            "using S3 as an intermediary. The S3 object is always cleaned up."
        ),
    )
    parser.add_argument("env", help="Environment name (cluster will be mavis-ENV)")
    parser.add_argument("local_file", help="Path to the local file to upload")
    parser.add_argument("remote_path", help="Destination path inside the container")
    parser.add_argument(
        "--task-id",
        dest="task_id",
        help="Task ID to target (auto-resolved via the ops service)",
    )
    parser.set_defaults(func=run)


def run(args):
    env = args.env

    if not os.path.isfile(args.local_file):
        sys.exit(f"Error: Local file not found: {args.local_file}")

    ecs.confirm_production(env)
    ecs.ensure_authenticated()

    task_id = ecs.resolve_task_for_transfer(env, args.task_id)
    bucket = ecs.s3_bucket(env)
    key = f"temp-{secrets.token_hex(8)}"
    s3_uri = f"s3://{bucket}/{key}"

    print(f"Uploading {args.local_file} to {s3_uri} ...")
    upload = subprocess.run(
        ["aws", "s3", "cp", args.local_file, s3_uri, "--region", ecs.REGION]
    )
    if upload.returncode != 0:
        sys.exit("Error: Failed to upload file to S3")

    try:
        print(f"Downloading from S3 into task {task_id} at {args.remote_path} ...")
        exit_code = ecs.run_command(
            env,
            task_id,
            f"aws s3 cp {s3_uri} {args.remote_path} --region {ecs.REGION}",
        )
    finally:
        subprocess.run(
            ["aws", "s3", "rm", s3_uri, "--region", ecs.REGION],
            capture_output=True,
        )

    if exit_code != 0:
        sys.exit("Error: Failed to copy file into container")
    print("File successfully uploaded to container")


