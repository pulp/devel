import argparse

from . import releng


def main():
    parser = argparse.ArgumentParser(prog='Pulp development tools')
    subparsers = parser.add_subparsers()

    releng.add_subcommands(subparsers)

    # Execute the selected function
    args = parser.parse_args()
    args.func(args)
