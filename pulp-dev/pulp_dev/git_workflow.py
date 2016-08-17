"""
This module contains functions related to our git workflow, such as autodiscovering branch
promotion chains and merging branches forward.
"""

import re
import shlex
import subprocess
import sys
from itertools import tee

from distutils.version import LooseVersion


def promotion_chain(git_directory, commit_ref, parent_branch=None, skip_master=False):
    """
    For a given git repository directory & branch/tag, determine the promotion chain

    Following the promotion path defined for pulp figure out what the full promotion
    path to master is from wherever we are.

    For example if given 2.5-release for pulp the promotion path
    would be 2.5-release -> 2.5-dev -> 2.6-dev -> master

    commit_ref, or parent_branch if commit_ref is a tag, must be a branch in the
    normal Pulp branching scheme, named x.y-dev or x.y-release. Release branches
    will be merged into the -dev branch for the same version, and then merged forward
    through newer dev branches to master (unless skip_master is True).

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :param commit_ref: The git branch to start with. If this is a tag, parent_branch must be set.
    :type commit_ref: str
    :param parent_branch: Parent branch that should be prepended to the promotion chain. This
                          is used for building from a tag, such as in a hotfix release.
    :type parent_branch: str
    :param skip_master: If True, don't promote all the way forward to master. Useful for
        when master is a newer major version than the branch being promoted.
        :return: list of branches that the specified branch promotes to
    :type skip_master: bool
    :rtype: list of str
    """
    # This can somtimes come from the yaml with trailing whitespace
    commit_ref = commit_ref.strip()

    # This is unlikely, but if for some reason commit_ref is master,
    # it's already promoted and we can short out
    if commit_ref == 'master':
        return ['master']

    # only work with the upstream repo cloned under the remote named "origin"
    remote_name = 'origin'

    if parent_branch:
        # parent_branch is set, so commit_ref should be a tag that will get merged
        # into its parent, and merged forward from there
        promotion_chain = [commit_ref, parent_branch]
    else:
        # no parent branch, commit_ref begins the promotion chain
        promotion_chain = [commit_ref]

    # parse the commit_ref: x.y-(dev|testing|release)
    branch_regex = "(?P<version>\d+.\d+)-(?P<stream>dev|release)"

    # start at the end of the current promotion chain (commit_ref or parent_branch as appropriate)
    start_ref = promotion_chain[-1]
    match = re.search(branch_regex, start_ref)
    if not match:
        raise ValueError('{} is not a valid branch from which to merge forward, '
                         'must be an x.y-dev or x.y-release branch.').format(start_ref)
    match_dict = match.groupdict()
    source_branch_version = match_dict['version']
    source_branch_major = source_branch_version.split('.', 1)[0]
    source_branch_stream = match_dict['stream']

    # if the starting ref is a release branch, bring it forward to its dev branch first
    if source_branch_stream == 'release':
        promotion_chain.append("{}-dev".format(source_branch_version))

    # get the branch list
    raw_branch_list = subprocess.check_output(['git', 'branch', '-r'], cwd=git_directory)
    lines = raw_branch_list.splitlines()

    target_branch_versions = set()
    all_branches = set()
    for branch in lines:
        branch = branch.strip()
        match = re.search(branch_regex, branch)
        if match:
            match_dict = match.groupdict()
            branch_version = match_dict['version']
            branch_major = branch_version.split('.', 1)[0]
            all_branches.add(branch_version)
            # accept branches as potential merge-forward targets if they are a
            # higher version, but not from a higher major version (don't automatically
            # merge 2.y-dev branches forward into 3.y-dev branches
            if (LooseVersion(branch_version) > LooseVersion(source_branch_version) and
                    branch_major == source_branch_major):
                target_branch_versions.add(branch_version)

    # version-sort the target versions (implictly converts to list)
    target_branch_versions = sorted(target_branch_versions, key=LooseVersion)

    # add all -dev branches with higher versions to the promotion chain
    promotion_chain.extend(['{}-dev'.format(version) for version in target_branch_versions])

    # make sure the expected -dev branches actually exist before trying to merge to them
    missing_branches = set(target_branch_versions).difference(all_branches)
    if missing_branches:
        print("Error creating git branch promotion list.  The following branches are missing:")
        print(missing_branches)
        sys.exit(1)

    # finally, append master to the promotion chain unless skip_master was requested
    if not skip_master:
        promotion_chain.append('master')

    # append the 'origin/' to each branch to give git what it needs to do the work
    return ["{}/{}".format(remote_name, branch_name) for branch_name in promotion_chain]


def generate_promotion_pairs(promotion_chain):
    """
    For all the items in a promotion path, yield (src, dest) promotions

    :param promotion_chain: list of branches that will need to be promoted
    :type promotion_chain: list of str
    """
    # split the promotion chain into two iterables, advance the second, and yield zipped pairs
    src, dest = tee(promotion_chain)
    next(dest)
    return zip(src, dest)


def check_merge_forward(git_directory, promotion_chain):
    """
    For a given git repo & promotion path, validate that all branches have been merged forward

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :param promotion_chain: git branch promotion path
    :type promotion_chain: list of str
    """
    for src, dest in generate_promotion_pairs(promotion_chain):
        print("checking log comparision of {} -> {}".format(src, dest))
        command = 'git log "^{}" "{}"'.format(dest, src)
        # the git log command should have no output if dest contains src hashes
        if subprocess.check_output(shlex.split(command), cwd=git_directory):
            raise RuntimeError("ERROR: in {}: branch {} has not been merged into {}".format(
                    git_directory, src, dest))


def upstream_branch_name(git_directory):
    """
    For a given git directory, get the current remote branch

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :return: remote branch
    :rtype: str
    """
    command = 'git rev-parse --abbrev-ref --symbolic-full-name @{u}'
    return subprocess.check_output(shlex.split(command), cwd=git_directory).strip()


def current_branch_name(git_directory):
    """
    For a given git directory, get the current branch

    :param git_directory: The directory containing the git repo
    :type git_directory: str
    :return: remote branch
    :rtype: str
    """
    command = 'git rev-parse --abbrev-ref HEAD'
    return subprocess.check_output(shlex.split(command), cwd=git_directory).strip()


def local_commit_refs(git_directory):
    command = "git for-each-ref --format %(refname:short) refs/heads/"
    output = subprocess.check_output(shlex.split(command), cwd=git_directory)
    return set(line.strip() for line in output.splitlines())


def checkout_branch(git_directory, treeish):
    """
    Ensure that treeish is checkout from the given upstream

    :param git_directory: directory containing the git project
    :type git_directory:  str
    :param treeish: The ref to check out from the 'origin' remote.
    :type treeish: str
    """
    # fetch the remote ref
    fetch = 'git fetch origin {}'.format(treeish)
    subprocess.check_call(shlex.tokenize(fetch), cwd=git_directory)

    # ensure the local ref for the remote branch is cleaned out
    clean_local = 'git branch -D {}'.format(treeish)
    # might fail if the branch doesn't already exist, so don't check_call, just call
    subprocess.call(shlex.tokenize(clean_local), cwd=git_directory)

    # name the local ref to match the remote
    checkout = 'git checkout -b {} FETCH_HEAD'.format(treeish)
    subprocess.check_call(shlex.tokenize(checkout), cwd=git_directory)


def merge_forward(git_directory, push=False, parent_branch=None, skip_master=False):
    """
    Given a checked-out git repository, merge the checked-out branch forward.

    :param git_directory: directory containing the git project
    :type git_directory:  str
    :param push: Whether or not we should push the results to github
    :type push: bool
    :param parent_branch: Parent branch that should be prepended to the promotion chain. This
                          is used for building from a tag, such as in a hotfix release.
    :type parent_branch: str
    :param skip_master: If True, don't promote all the way forward to master. Useful for
        when master is a newer major version than the branch being promoted.
        :return: list of branches that the specified branch promotes to
    :type skip_master: bool
    """
    starting_branch = current_branch_name(git_directory)
    branch = upstream_branch_name(git_directory)
    chain = promotion_chain(git_directory, branch, parent_branch, skip_master)

    for source_branch, target_branch in generate_promotion_pairs(chain):
        checkout_branch(git_directory, source_branch)
        checkout_branch(git_directory, target_branch)
        local_source_branch = source_branch.split('/')[1]
        print("Merging {} into {}".format(local_source_branch, target_branch))
        subprocess.check_call(['git', 'merge', '-s', 'ours', local_source_branch, '--no-edit'],
                              cwd=git_directory)
        if push:
            subprocess.call(['git', 'push', '-v'], cwd=git_directory)

    # check the starting branch out, leaving the git repo on the same branch it was on
    checkout_branch(git_directory, starting_branch)
