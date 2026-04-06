import argparse
import sys

from mavis_server import ecs, get_file, put_file, shell


def main():
    parser = argparse.ArgumentParser(
        prog="mavis-server",
        description="MAVIS server management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    shell.register(subparsers)
    put_file.register(subparsers)
    get_file.register(subparsers)

    args = parser.parse_args()
    try:
        args.func(args)
    except ecs.ECSError as e:
        sys.exit(str(e))
