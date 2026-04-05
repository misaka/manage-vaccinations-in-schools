import argparse
import sys

from mavis_server import shell


def main():
    parser = argparse.ArgumentParser(
        prog="mavis-server",
        description="MAVIS server management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    shell.register(subparsers)

    args = parser.parse_args()
    try:
        args.func(args)
    except ecs.ECSError as e:
        sys.exit(str(e))
