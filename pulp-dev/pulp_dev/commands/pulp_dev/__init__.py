import argparse

from . import releng
from . import git_workflow
# from . import versions


def main():
    parser = argparse.ArgumentParser(description='Pulp development tools')
    subparsers = parser.add_subparsers(dest='subparser_name')

    releng.add_subcommands(subparsers)
    git_workflow.add_subcommands(subparsers)
    # versions.subcommands(subparsers)

    # Execute the selected function
    args = parser.parse_args()
    if args.subparser_name:
        args.func(args)
    else:
        parser.error('A sub-command must be specified.')
