import argparse

import get_file
import put_file
import shell


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
    args.func(args)
