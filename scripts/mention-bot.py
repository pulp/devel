#!/usr/bin/env python3
"""Automatic config maker for mention-bot by facebook.

Made for ver. a7ed44ed1383416f463c163b3086e9562f0e1a4a
"""

from os.path import join, expanduser, expandvars, exists
from distutils.util import strtobool
import sys
import json
import argparse
import time

PULP_PATH = "~/devel"
PULP_REPOS = ['crane', 'pulp', 'pulp_docker', 'pulp_ostree', 'pulp_puppet', 'pulp_python',
              'pulp_rpm']

GITHUB_URL = "https://github.com/pulp/{repo}/compare/master...{username}:{branch}?expand=1"

try:
    import git
    GIT_AVAILIBLE = True
except ImportError:
    GIT_AVAILIBLE = False

def check_git():
    """Exit if git library isn't present."""
    if not GIT_AVAILIBLE:
        print("Error git functions are unavailible you have to install gitpython.")
        print("$ pip3 install gitpython")
        sys.exit(1)

def find(list_, func):
    """Find element in list.

    Func takes ele and return if True if we have found the element we want.
    example:
    >> l = [{"name": "John"}, {"name": Alex}]
    >> find(l, lambda dic: dic["name"] == "John")
    0

    raise ValueError if not found.
    """
    for i, element in enumerate(list_):
        if func(element):
            return i
    raise ValueError

def repo_path(repo):
    """Get path to the repository.

    exapandvars - In path can be used ENV variables
    expanduser - ~ is replaced by value of $HOME
    """
    return expandvars(expanduser(join(PULP_PATH, repo)))

def config_path(repo):
    """Get path to .mention-bot via repo_path()."""
    return join(repo_path(repo), ".mention-bot")


def read_config(path):
    """Load json from fie on path."""
    with open(path, "r") as infile:
        return json.load(infile)


def write_config(path, data):
    """Write JSON dump into file on path."""
    with open(path, 'w') as outfile:
        json.dump(data, outfile, indent=4)


def parse_config(repo):
    """From name of repo create path and call read_config."""
    return read_config(config_path(repo))


def save_config(repo, data):
    """From name of repo create path and call write_config with supplied data."""
    write_config(config_path(repo), data)


def json_print(config):
    """Print idented sorted JSON to stdout."""
    print(json.dumps(config, indent=4, sort_keys=True))


def print_nice_separator(repo):
    """Print 80 characters long seperator between repos."""
    print("*"*80)
    print(("*"*30 + " REPO: %s " % repo).ljust(80, "*"))
    print("*"*80)


def pretty_print(config):
    """Verbously with names explain config file."""
    print("* Maximum Reviewers to ping: %d" % config.get("maxReviewers", 3))
    print("* Number of files to check against: %d" % config.get("numFilesToCheck", 5))
    print("* Message: \"%s\"" % config.get(
        "message", "@pullRequester, thanks for your PR! By analyzing the history of the files in "
        "this pull request, we identified @reviewers to be potential reviewers."))
    print("* Users to be always notified on certain files:")
    alwaysNotifyForPaths_list = config.get("alwaysNotifyForPaths", [])
    alwaysNotifyForPaths_list_max_i = len(alwaysNotifyForPaths_list) - 1
    for i, user in enumerate(alwaysNotifyForPaths_list):
        print("  * Name: %s" % user["name"])
        print("  * Files:")
        for f in user["files"]:
            print("    * \"%s\"" % f)
        print("  * Skip user's team in mentioning: " + str(user["skipTeamPrs"]))
        if i < alwaysNotifyForPaths_list_max_i:
            print("  ----------------------------------------")
    print("* Fallback users if no user was found:")
    fallbackNotifyForPaths_list = config.get("fallbackNotifyForPaths", [])
    fallbackNotifyForPaths_list_max_i = len(fallbackNotifyForPaths_list) - 1
    for i, user in enumerate(fallbackNotifyForPaths_list):
        print("  * Name: %s" % user["name"])
        print("  * Files:")
        for f in user["files"]:
            print("    * \"%s\"" % f)
        print("  * Skip user's team in mentioning: " + str(user["skipTeamPrs"]))
        if i < fallbackNotifyForPaths_list_max_i:
            print("  ----------------------------------------")
    print("* Find potential reviewers: " + str(config.get("findPotentialReviewers", True)))
    print("* File black list:")
    for f in config.get("fileBlacklist", []):
        print("  * \"%s\"" % f)
    print("* Reviewers black list:")
    for u in config.get("userBlacklist", []):
        print("  * %s" % u)
    print("* PR Authors black list:")
    for u in config.get("userBlacklistForPR", []):
        print("  * %s" % u)
    print("* Reviewers required organization:")
    for u in config.get("requiredOrgs", []):
        print("  * %s" % u)
    print("* Actions to which mention-bot is listening")
    for u in config.get("actions", ["opened"]):
        print("  * %s" % u)
    print("* Skip already assigned PRs: " + str(config.get("skipAlreadyAssignedPR", False)))
    print("* Skip PRs which already mentions somebody: " + str(
            config.get("skipAlreadyMentionedPR", False)))
    print("* Assign PR to most appropriate reviewer: " + str(
            config.get("assignToReviewer", False)))
    print("* Create review request for PR to most appropriate reviewer: " + str(
            config.get("createReviewRequest", False)))
    print("* Comment PR mentioning appropriate reviewers: " + str(
            config.get("createComment", True)))
    print("* Skip PRs which have in title: \"%s\"" % config.get("skipTitle", ""))
    print("* Only work on PRs with label(actions have to be set to \"labeld\"): \"%s\"" % (
            config.get("withLabel", "")))
    print("* Delay mention bot action: " + str(config.get("delayed", False)))
    print("* Delay for: %s" % config.get("delayedUntil", ""))
    print("* Ignore PR if it's made by collaborator: " + str(config.get("skipCollaboratorPR", False)))


def jprint_command(args):
    """Print .metion-bot JSON config file of specified repositories."""
    for repo in args.repo or PULP_REPOS:
        if exists(config_path(repo)):
            if args.repo is None or len(args.repo or []) > 1:
                print_nice_separator(repo)
            json_print(parse_config(repo))
        elif args.repo is not None:
            print("ERROR: repo %s not found")


def print_command(args):
    """Print .metion-bot config in human way for specified repositories."""
    for repo in args.repo or PULP_REPOS:
        if exists(config_path(repo)):
            if args.repo is None or len(args.repo or []) > 1:
                print_nice_separator(repo)
            pretty_print(parse_config(repo))
        elif args.repo is not None:
            print("ERROR: repo %s not found")


def set_command(args):
    """Set values in mention-bot config.

    Works on fields:
    * maxReviewers
    * numFilesToCheck
    * message
    * findPotentialReviewers
    * skipAlreadyAssignedPR
    * skipAlreadyMentionedPR
    * assignToReviewer
    * createReviewRequest
    * createComment
    * delayed
    * skipCollaboratorPR
    """
    for repo in args.repo or PULP_REPOS:
        if exists(config_path(repo)):
            if args.username is not None and not args.human_print_only and not args.print_only:
                check_git()
                grepo = git.Repo(repo_path(repo))
                grepo.git.stash("-u") # Stash repository
                old_head = grepo.head.reference # Save branch
                grepo.heads.master.checkout()
                new_branch = grepo.create_head('mention-bot' + str(int(time.time())))
                new_branch.checkout()
            conf = parse_config(repo)
            if args.var == "maxReviewers":
                conf["maxReviewers"] = args.number_of_users
            elif args.var == "numFilesToCheck":
                conf["numFilesToCheck"] = args.number_of_files
            elif args.var == "message":
                conf["message"] = args.message
            elif args.var in ["findPotentialReviewers", "skipAlreadyAssignedPR",
                              "skipAlreadyMentionedPR", "assignToReviewer", "createReviewRequest",
                              "createComment", "delayed", "skipCollaboratorPR"]:
                conf[args.var] = bool(args.bool)
            elif args.var == "skipTitle":
                conf["skipTitle"] = args.title
            elif args.var == "withLabel":
                conf["withLabel"] = args.label
            elif args.var == "delayedUntil":
                conf["delayedUntil"] = args.time
            if (args.human_print_only or args.print_only) and (
                    args.repo is None or len(args.repo or []) > 1):
                print_nice_separator(repo)
            if args.human_print_only:
                pretty_print(conf)
            if args.print_only:
                json_print(conf)
            if not args.print_only and not args.human_print_only:
                save_config(repo, conf)
                if args.username is not None:
                    unstaged = grepo.index.diff(None)
                    changed = False
                    for u in unstaged:
                        if u.b_path == ".mention-bot" and u.change_type == "M":
                            changed = True
                    if not changed and ".mention-bot" in grepo.untracked_files:
                        changed = True
                    if changed:
                        grepo.index.add([".mention-bot"])
                        grepo.index.commit(args.commit_message or "Update .mention-bot")
                        print("Last chance to stop me from push... (10s) exit with Ctrl^C \n"
                              "Your current unstaged changes have been stashed.")
                        time.sleep(10)
                        getattr(grepo.remotes, args.remote).push(new_branch.name)
                        print("Please create PR on page:")
                        print(GITHUB_URL.format(repo=repo, username=args.username,
                                                branch=new_branch.name))
                    else:
                        new_branch.delete(grepo, new_branch)
                    old_head.checkout()
                    grepo.git.stash("pop") # Unstash repository
        elif args.repo is not None:
            print("ERROR: repo %s not found")


def append_command(args):
    """Append values to config.

    Works on fields:
    * userBlacklist
    * fileBlacklist
    * userBlacklistForPR
    * requiredOrgs
    * actions
    * alwaysNotifyForPaths
    * fallbackNotifyForPaths
    """
    for repo in args.repo or PULP_REPOS:
        if exists(config_path(repo)):
            if args.username is not None and not args.human_print_only and not args.print_only:
                check_git()
                grepo = git.Repo(repo_path(repo))
                grepo.git.stash("-u") # Stash repository
                old_head = grepo.head.reference # Save branch
                grepo.heads.master.checkout()
                new_branch = grepo.create_head('mention-bot' + str(int(time.time())))
                new_branch.checkout()
            conf = parse_config(repo)
            if args.var == "userBlacklist":
                for u in args.user:
                    if u not in conf.get("userBlacklist", []):
                        conf.setdefault("userBlacklist", []).append(u)
            elif args.var == "fileBlacklist":
                for f in args.file:
                    if f not in conf.get("fileBlacklist", []):
                        conf.setdefault("fileBlacklist", []).append(f)
            elif args.var == "userBlacklistForPR":
                for u in args.user:
                    if u not in conf.get("userBlacklistForPR", []):
                        conf.setdefault("userBlacklistForPR", []).append(u)
            elif args.var == "requiredOrgs":
                for o in args.org:
                    if o not in conf.get("requiredOrgs", []):
                        conf.setdefault("requiredOrgs", []).append(o)
            elif args.var == "actions":
                for a in args.action:
                    if a not in conf.get("actions", []):
                        if a is not "opened":
                            conf.setdefault("actions", ["opened"]).append(a)
                        else:
                            conf.setdefault("actions", []).append(a)
            elif args.var in ["alwaysNotifyForPaths", "fallbackNotifyForPaths"]:
                list_ = conf.setdefault(args.var, [])
                try:
                    i = find(list_, lambda element: element["name"] == args.name)
                    for f in args.file:
                        if f not in list_[i]["files"]:
                            list_[i]["files"].append(f)
                    list_[i]["skipTeamPrs"] = bool(args.skipTeamPrs)
                except ValueError:
                    list_.append({
                        "name": args.name,
                        "files": args.file,
                        "skipTeamPrs": bool(args.skipTeamPrs)
                        })
            if (args.human_print_only or args.print_only) and (
                    args.repo is None or len(args.repo or []) > 1):
                print_nice_separator(repo)
            if args.human_print_only:
                pretty_print(conf)
            if args.print_only:
                json_print(conf)
            if not args.print_only and not args.human_print_only:
                save_config(repo, conf)
                if args.username is not None:
                    unstaged = grepo.index.diff(None)
                    changed = False
                    for u in unstaged:
                        if u.b_path == ".mention-bot" and u.change_type == "M":
                            changed = True
                    if not changed and ".mention-bot" in grepo.untracked_files:
                        changed = True
                    if changed:
                        grepo.index.add([".mention-bot"])
                        grepo.index.commit(args.commit_message or "Update .mention-bot")
                        print("Last chance to stop me from push... (10s) exit with Ctrl^C \n"
                              "Your current unstaged changes have been stashed.")
                        time.sleep(10)
                        getattr(grepo.remotes, args.remote).push(new_branch.name)
                        print("Please create PR on page:")
                        print(GITHUB_URL.format(repo=repo, username=args.username,
                                                branch=new_branch.name))
                    else:
                        new_branch.delete(grepo, new_branch)
                    old_head.checkout()
                    grepo.git.stash("pop") # Unstash repository
        elif args.repo is not None:
            print("ERROR: repo %s not found")


def remove_command(args):
    """Remove vlaues from fields in config.

    Works on fields:
    * userBlacklist
    * fileBlacklist
    * userBlacklistForPR
    * requiredOrgs
    * actions
    * alwaysNotifyForPaths
    * fallbackNotifyForPaths
    """
    for repo in args.repo or PULP_REPOS:
        if exists(config_path(repo)):
            if args.username is not None and not args.human_print_only and not args.print_only:
                check_git()
                grepo = git.Repo(repo_path(repo))
                grepo.git.stash("-u") # Stash repository
                old_head = grepo.head.reference # Save branch
                grepo.heads.master.checkout()
                new_branch = grepo.create_head('mention-bot' + str(int(time.time())))
                new_branch.checkout()
            conf = parse_config(repo)
            if args.var == "userBlacklist":
                for u in args.user:
                    if u in conf.get("userBlacklist", []):
                        conf.get("userBlacklist").remove(u)
            elif args.var == "fileBlacklist":
                for f in args.file:
                    if f in conf.get("fileBlacklist", []):
                        conf.get("fileBlacklist").remove(f)
            elif args.var == "userBlacklistForPR":
                for u in args.user:
                    if u in conf.get("userBlacklistForPR", []):
                        conf.get("userBlacklistForPR").remove(u)
            elif args.var == "requiredOrgs":
                for o in args.org:
                    if o in conf.get("requiredOrgs", []):
                        conf.get("requiredOrgs").remove(o)
            elif args.var == "actions":
                for a in args.action:
                    if a in conf.get("actions", []):
                        conf.get("actions").remove(a)
            elif (args.var in ["alwaysNotifyForPaths", "fallbackNotifyForPaths"] and
                    args.var in conf):
                i = find(conf[args.var], lambda element: element["name"] == args.name)
                if len(args.file) is 0:
                    del conf[args.var][i]
                else:
                    for f in args.file:
                        if f in conf[args.var][i]["files"]:
                            conf[args.var][i]["files"].remove(f)
                if len(conf[args.var]) == 0:
                    del conf[args.var]
            if (args.human_print_only or args.print_only) and (
                    args.repo is None or len(args.repo or []) > 1):
                print_nice_separator(repo)
            if args.human_print_only:
                pretty_print(conf)
            if args.print_only:
                json_print(conf)
            if not args.print_only and not args.human_print_only:
                save_config(repo, conf)
                if args.username is not None:
                    unstaged = grepo.index.diff(None)
                    changed = False
                    for u in unstaged:
                        if u.b_path == ".mention-bot" and u.change_type == "M":
                            changed = True
                    if not changed and ".mention-bot" in grepo.untracked_files:
                        changed = True
                    if changed:
                        grepo.index.add([".mention-bot"])
                        grepo.index.commit(args.commit_message or "Update .mention-bot")
                        print("Last chance to stop me from push... (10s) exit with Ctrl^C \n"
                              "Your current unstaged changes have been stashed.")
                        time.sleep(10)
                        getattr(grepo.remotes, args.remote).push(new_branch.name)
                        print("Please create PR on page:")
                        print(GITHUB_URL.format(repo=repo, username=args.username,
                                                branch=new_branch.name))
                    else:
                        new_branch.delete(grepo, new_branch)
                    old_head.checkout()
                    grepo.git.stash("pop") # Unstash repository
        elif args.repo is not None:
            print("ERROR: repo %s not found")


def sync_command(args):
    """Unify content from all repos and then save it back.

    Working on fields:
    * userBlacklist
    * userBlacklistForPR
    * requiredOrgs
    """
    output_set = set([])
    for repo in args.repo or PULP_REPOS:
        if exists(config_path(repo)):
            conf = parse_config(repo)
            output_set.update(conf[args.var])
        elif args.repo is not None:
            print("ERROR: repo %s not found")

    output_list = list(output_set)
    for repo in args.repo or PULP_REPOS:
        if exists(config_path(repo)):
            conf = parse_config(repo)
            conf[args.var] = output_list
            if (args.human_print_only or args.print_only) and (
                    args.repo is None or len(args.repo or []) > 1):
                print_nice_separator(repo)
            if args.human_print_only:
                pretty_print(conf)
            if args.print_only:
                json_print(conf)
            if not args.print_only and not args.human_print_only:
                save_config(repo, conf)
        elif args.repo is not None:
            print("ERROR: repo %s not found")


def main():
    """Setup argparse and call subcommand function."""
    repo_parser = argparse.ArgumentParser(add_help=False)
    repo_parser.add_argument("--repo", type=str, choices=PULP_REPOS, nargs='+',
                             help="Repositories to do action on. If empty action will be appliad "
                             "to all repositories. You can specify more than one repository.")

    debug_parser = argparse.ArgumentParser(add_help=False)
    debug_parser.add_argument("-p", "--print-only", action="store_true",
                              help="Do not save changes, only print json result.")
    debug_parser.add_argument("-hp", "--human-print-only", action="store_true",
                              help="Do not save changes, only human redable result.")

    git_parser = argparse.ArgumentParser(add_help=False)
    git_parser.add_argument("-c", "--commit", dest="username",
                            help="Create commit in new PR. WARNING EXPERIMENTAL FEATURE WORK ONLY "
                            "IF HEAD IS NOT DETACHED.")
    git_parser.add_argument("-cm", "--commit-message",
                            help="Message to be used when creating commit.")

    git_parser.add_argument("--remote", default="origin",
                            help="The remote to push the commit. Default \"origin\". WARNING!! "
                            "BE ASURE THAT THIS REMOTE ISN'T UPSTREAM REPOSITORY!!!")

    parser = argparse.ArgumentParser(description="Mention bot Pulp central edit utility")
    subparsers = parser.add_subparsers(title='Commands', dest="command")
    subparsers.required = True

    print_parser = subparsers.add_parser("print", parents=[repo_parser], aliases=["p"],
                                         help="Print .metion-bot config")
    print_parser.set_defaults(func=print_command)

    print_parser = subparsers.add_parser("jprint", parents=[repo_parser], aliases=["jp"],
                                         help="Print json .metion-bot config")
    print_parser.set_defaults(func=jprint_command)

    # ################################# Set ################################################

    set_parser = subparsers.add_parser("set", aliases=["s"],
                                       help="Set value", description="By this command you can set "
                                       "values in config.")
    set_parser.set_defaults(func=set_command)

    set_subparser = set_parser.add_subparsers(
        title="Setable variables", help="variables", dest="var",
        description="You can set these variables")
    set_subparser.required = True

    # maxReviewers
    set_max_reviews = set_subparser.add_parser(
        "maxReviewers", parents=[repo_parser, debug_parser, git_parser],
        help="Maximum  number of people to ping in the PR message, default is 3",
        description="Maximum  number of people to ping in the PR message, default is 3")
    set_max_reviews.add_argument("number_of_users", type=int, default=3)

    # numFilesToCheck
    set_num_of_files = set_subparser.add_parser(
        "numFilesToCheck", parents=[repo_parser, debug_parser, git_parser],
        help="Number of files to check against, default is 5",
        description="Number of files to check against, default is 5")
    set_num_of_files.add_argument("number_of_files", type=int, default=5)

    # message
    set_message = set_subparser.add_parser(
        "message", parents=[repo_parser, debug_parser, git_parser],
        help="custom message using @pullRequester and @reviewers",
        description="custom message using @pullRequester and @reviewers")
    set_message.add_argument(
        "message", type=str,
        default="@pullRequester, thanks for your PR! By analyzing the history of the files in "
        "this pull request, we identified @reviewers to be potential reviewers.")

    # findPotentialReviewers
    set_find_potential = set_subparser.add_parser(
        "findPotentialReviewers", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will try to find potential reviewers based on files history, "
             "if disabled, `alwaysNotifyForPaths` is used instead",
        description="mention-bot will try to find potential reviewers based on files history, if "
                    "disabled, `alwaysNotifyForPaths` is used instead")
    set_find_potential.add_argument("bool", type=strtobool)

    # skipAlreadyAssignedPR
    set_skip_assigned = set_subparser.add_parser(
        "skipAlreadyAssignedPR", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will ignore already assigned PR's",
        description="mention-bot will ignore already assigned PR's")
    set_skip_assigned.add_argument("bool", type=strtobool)

    # skipAlreadyMentionedPR
    set_skip_mentioned = set_subparser.add_parser(
        "skipAlreadyMentionedPR", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will ignore if there is already existing an exact mention",
        description="mention-bot will ignore if there is already existing an exact mention")
    set_skip_mentioned.add_argument("bool", type=strtobool)

    # assignToReviewer
    set_assign_reviewer = set_subparser.add_parser(
        "assignToReviewer", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot assigns the most appropriate reviewer for PR",
        description="mention-bot assigns the most appropriate reviewer for PR")
    set_assign_reviewer.add_argument("bool", type=strtobool)

    # createReviewRequest
    set_creat_request = set_subparser.add_parser(
        "createReviewRequest", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot creates review request for the most appropriate reviewer for PR",
        description="mention-bot creates review request for the most appropriate reviewer for PR")
    set_creat_request.add_argument("bool", type=strtobool)

    # createComment
    set_creat_comment = set_subparser.add_parser(
        "createComment", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot creates a comment mentioning the reviewers for the PR",
        description="mention-bot creates a comment mentioning the reviewers for the PR")
    set_creat_comment.add_argument("bool", type=strtobool)

    # skipTitle
    set_skip_title = set_subparser.add_parser(
        "skipTitle", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will ignore PR that includes text in the title",
        description="mention-bot will ignore PR that includes text in the title")
    set_skip_title.add_argument("title", type=str)

    # withLabel
    set_skip_label = set_subparser.add_parser(
        "withLabel", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will only consider PR's with this label. Must set actions to "
             "[\"labeled\"].",
        description="mention-bot will only consider PR's with this label. Must set actions to "
                    "[\"labeled\"].")
    set_skip_label.add_argument("label", type=str)

    # delayed
    set_delayed = set_subparser.add_parser(
        "delayed", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will wait to comment until specified time in `delayedUntil` value",
        description="mention-bot will wait to comment until specified time in `delayedUntil` value")
    set_delayed.add_argument("bool", type=strtobool)

    # delayedUntil
    set_delayed_until = set_subparser.add_parser(
        "delayedUntil", parents=[repo_parser, debug_parser, git_parser],
        help="Used if delayed is equal true.",
        description="Used if delayed is equal true, permitted values are: minutes, hours, or "
                    "days, e.g.: '3 days', '40 minutes', '1 hour', '3d', '1h', '10m'")
    set_delayed_until.add_argument("time", type=str)

    # skipCollaboratorPR
    set_skip_colaborator = set_subparser.add_parser(
        "skipCollaboratorPR", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will ignore if PR is made by collaborator",
        description="mention-bot will ignore if PR is made by collaborator")
    set_skip_colaborator.add_argument("bool", type=strtobool)

    # ################################# Append #############################################
    append_parser = subparsers.add_parser("append", aliases=["a"],
                                          help="Append new value",
                                          description="By this command you can append values into "
                                                      "some of the lists in config.")
    append_parser.set_defaults(func=append_command)

    append_subparser = append_parser.add_subparsers(
        title="Appendable variables", help="variables", dest="var",
        description="Into these variables you can append new values.")
    append_subparser.required = True

    # userBlacklist
    append_user_black_list = append_subparser.add_parser(
        "userBlacklist", parents=[repo_parser, debug_parser, git_parser],
        help="Users in this list will never be mentioned by mention-bot",
        description="Users in this list will never be mentioned by mention-bot")
    append_user_black_list.add_argument("user", type=str, nargs="+",)

    # fileBlacklist
    append_file_black_list = append_subparser.add_parser(
        "fileBlacklist", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will ignore any files that match these file globs (\"*.md\")",
        description="mention-bot will ignore any files that match these file globs (\"*.md\")")
    append_file_black_list.add_argument("file", type=str, nargs="+",)

    # userBlacklistForPR
    append_user_black_list_for_pr = append_subparser.add_parser(
        "userBlacklistForPR", parents=[repo_parser, debug_parser, git_parser],
        help="PR made by users in this list will be ignored",
        description="PR made by users in this list will be ignored")
    append_user_black_list_for_pr.add_argument("user", type=str, nargs="+",)

    # requiredOrgs
    append_req_orgs = append_subparser.add_parser(
        "requiredOrgs", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will only mention user who are a member of one of these organizations",
        description="mention-bot will only mention user who are a member of one of these "
        "organizations")
    append_req_orgs.add_argument("org", type=str, nargs="+",)

    # actions
    append_actions = append_subparser.add_parser(
        "actions", parents=[repo_parser, debug_parser, git_parser],
        help="List of PR actions that mention-bot will listen to, default is \"opened\"",
        description="List of PR actions that mention-bot will listen to, default is \"opened\"")
    append_actions.add_argument("action", type=str, nargs="+",)

    # alwaysNotifyForPaths
    append_always_notify = append_subparser.add_parser(
        "alwaysNotifyForPaths", parents=[repo_parser, debug_parser, git_parser],
        help="Users will always be mentioned based on file glob.",
        description="Users will always be mentioned based on file glob.")
    append_always_notify.add_argument("name", type=str, help="The user's Github username")
    append_always_notify.add_argument(
        "--skipTeamPrs", type=strtobool, default=False,
        help="mention-bot will exclude the creator's own team from mentions (default False)")
    append_always_notify.add_argument("file", type=str, nargs="*",
                                      help="The array of file globs associated with the user")

    # fallbackNotifyForPaths
    append_fallback_notify = append_subparser.add_parser(
        "fallbackNotifyForPaths", parents=[repo_parser, debug_parser, git_parser],
        help="Users will be mentioned based on file glob if no other user was found",
        description="Users will be mentioned based on file glob if no other user was found")
    append_fallback_notify.add_argument("name", type=str, help="The user's Github username")
    append_fallback_notify.add_argument(
        "--skipTeamPrs", type=strtobool, default=False,
        help="mention-bot will exclude the creator's own team from mentions (default False)")
    append_fallback_notify.add_argument(
        "file", type=str, nargs="*", help="The array of file globs associated with the user")

    # ################################# Remove #############################################

    remove_parser = subparsers.add_parser("remove", aliases=["r"],
                                          help="Remove value (Reverse append)",
                                          description="By this command you can remove values from "
                                          "lists in config. (Reverse operation for append)")
    remove_parser.set_defaults(func=remove_command)

    remove_subparser = remove_parser.add_subparsers(
        title="Removable variables", help="variables", dest="var",
        description="From these variables you can remove values.")
    remove_subparser.required = True

    # userBlacklist
    remove_user_black_list = remove_subparser.add_parser(
        "userBlacklist", parents=[repo_parser, debug_parser, git_parser],
        help="Users in this list will never be mentioned by mention-bot",
        description="Users in this list will never be mentioned by mention-bot")
    remove_user_black_list.add_argument("user", type=str, nargs="+",)

    # fileBlacklist
    remove_file_black_list = remove_subparser.add_parser(
        "fileBlacklist", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will ignore any files that match these file globs (\"*.md\")",
        description="mention-bot will ignore any files that match these file globs (\"*.md\")")
    remove_file_black_list.add_argument("file", type=str, nargs="+",)

    # userBlacklistForPR
    remove_user_black_list_for_pr = remove_subparser.add_parser(
        "userBlacklistForPR", parents=[repo_parser, debug_parser, git_parser],
        help="PR made by users in this list will be ignored",
        description="PR made by users in this list will be ignored")
    remove_user_black_list_for_pr.add_argument("user", type=str, nargs="+",)

    # requiredOrgs
    remove_req_orgs = remove_subparser.add_parser(
        "requiredOrgs", parents=[repo_parser, debug_parser, git_parser],
        help="mention-bot will only mention user who are a member of one of these organizations",
        description="mention-bot will only mention user who are a member of one of these "
        "organizations")
    remove_req_orgs.add_argument("org", type=str, nargs="+",)

    # actions
    remove_actions = remove_subparser.add_parser(
        "actions", parents=[repo_parser, debug_parser, git_parser],
        help="List of PR actions that mention-bot will listen to, default is \"opened\"",
        description="List of PR actions that mention-bot will listen to, default is \"opened\"")
    remove_actions.add_argument("action", type=str, nargs="+",)

    # alwaysNotifyForPaths
    remove_always_notify = remove_subparser.add_parser(
        "alwaysNotifyForPaths", parents=[repo_parser, debug_parser, git_parser],
        help="Users will always be mentioned based on file glob.",
        description="Users will always be mentioned based on file glob. When removing if file is "
        "not specified the whole user will be removed otherwise only specified files.")
    remove_always_notify.add_argument("name", type=str, help="The user's Github username")
    remove_always_notify.add_argument("file", type=str, nargs="*",
                                      help="The array of file globs to remove from the user")

    # fallbackNotifyForPaths
    remove_fallback_notify = remove_subparser.add_parser(
        "fallbackNotifyForPaths", parents=[repo_parser, debug_parser, git_parser],
        help="Users will be mentioned based on file glob if no other user was found",
        description="Users will be mentioned based on file glob if no other user was found. When "
        "removing if file is not specified the whole user will be removed otherwise only "
        "specified files.")
    remove_fallback_notify.add_argument("name", type=str, help="The user's Github username")
    remove_fallback_notify.add_argument(
        "file", type=str, nargs="*", help="The array of file globs to remove from the user")

    # ################################# Sync ###############################################

    sync_parser = subparsers.add_parser("sync",
                                       help="Sync across repos",
                                       description="By this command you can unify config values "
                                       "through repositories. So all present data will be merged.")
    sync_parser.set_defaults(func=sync_command)

    sync_subparser = sync_parser.add_subparsers(
        title="Syncable variables", help="variables", dest="var",
        description="You can sync these variables")
    sync_subparser.required = True

    # userBlacklist
    sync_subparser.add_parser(
        "userBlacklist", parents=[repo_parser, debug_parser],
        help="Users in this list will never be mentioned by mention-bot",
        description="Users in this list will never be mentioned by mention-bot")

    # userBlacklistForPR
    sync_subparser.add_parser(
        "userBlacklistForPR", parents=[repo_parser, debug_parser],
        help="PR made by users in this list will be ignored",
        description="PR made by users in this list will be ignored")

    # requiredOrgs
    sync_subparser.add_parser(
        "requiredOrgs", parents=[repo_parser, debug_parser],
        help="mention-bot will only mention user who are a member of one of these organizations",
        description="mention-bot will only mention user who are a member of one of these "
        "organizations")


    args = parser.parse_args()

    if getattr(args, "commit_message", None) is not None and getattr(args, "username", None) is None:
        parser.error("--commit-message requires --commit.")
    if args.func:
        args.func(args)

if __name__ == '__main__':
    main()
