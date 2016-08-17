"""
This module contains console command entry points for git workflow tools.
"""
from ... import git_workflow


def add_subcommands(subparsers):
    """
    Adds sub-commands provided for release engineering.
    """
    promoted_parser = subparsers.add_parser(
        'check-branch-promoted',
        description='Check that the named branch has been merged forward')
    promoted_parser.add_argument('git_directory', help='Path to git repository to check.')
    promoted_parser.add_argument('branch', help='Name of branch to check.')
    promoted_parser.add_argument('--skip_master', default=False, action='store_true',
                                 help='If set, leave master out of the branch promotion chain.')
    promoted_parser.set_defaults(func=check_branch_promoted)


def check_branch_promoted(args):
    promotion_chain = git_workflow.promotion_chain(args.git_directory, args.branch,
                                                   skip_master=args.skip_master)
    # throws and exception if branch not merged forward
    git_workflow.check_merge_forward(args.git_directory, promotion_chain)
    print("{} has been merged forward.".format(args.branch))
