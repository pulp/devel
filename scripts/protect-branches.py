#!/usr/bin/env python3


import argparse
import getpass
import json
import os
import re
import requests
import sys
import urllib


# API token received from github. For the "scopes", I only selected the entire "repo" section.
# https://github.com/settings/tokens
TOKEN = getpass.getpass(prompt='API token from GitHub: ')


# the Accept header tells github to let us use their experimental branch protection API
headers = {
    'Authorization': 'token {}'.format(TOKEN),
    'Accept': 'application/vnd.github.loki-preview+json',
}


# the body to send when setting protection on a branch
protection_body = json.dumps({'restrictions': None, 'required_status_checks': None})


name_re = re.compile('^master|.*-dev|.*-release$')


PULP_REPOS_URL = "https://api.github.com/repos/pulp/"


repo_names = (
    'crane',
    'devel',
    'nectar',
    'pulp',
    'pulp_docker',
    'pulp_ostree',
    'pulp_puppet',
    'pulp_python',
    'pulp_rpm',
)


def parse_args():
    parser = argparse.ArgumentParser(description='Sets branches on GitHub to be protected. '
                                     'Operates on master, *-release, and *-dev branches.')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List branches that should be protected but are not. '
                        'No changes will be made.')
    args = parser.parse_args()
    return args


def get_unprotected_branches(repo_name):
    """
    :param repo_name:   name of a repository that contains branches of interest
    :type  repo_name:   str

    :return:    generator of URLs to the protection endpoint of any branch that
                should be protected but currently is not
    :rtype:     generator
    """
    url = urllib.parse.urljoin(PULP_REPOS_URL, os.path.join(repo_name, 'branches'))
    response = requests.get(url, headers=headers)
    assert response.status_code == 200

    for branch in response.json():
        if name_re.match(branch['name']) and branch['protected'] is False:
            yield branch['protection_url']


def protect_branch(url):
    """
    :param url: URL for the protection endpoint of a branch that should be marked as protected
    :type  url: str
    """
    response = requests.put(url, headers=headers, data=protection_body)
    assert response.status_code == 200


if __name__ == '__main__':
    args = parse_args()
    list_only = args.list

    if not TOKEN:
        print('You must provide an API token from GitHub. https://github.com/settings/tokens')
        sys.exit(1)

    for name in repo_names:
        for branch_url in get_unprotected_branches(name):
            print(branch_url)
            if not list_only:
                protect_branch(branch_url)

