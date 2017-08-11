#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

import requests
import yaml

# Make a Python 3 virtualenv and install requests and PyYAML
#    pyvenv pulp_checkout
#    source pulp_checkout/bin/activate
#    pip install requests PyYAML
#
# Run the script using the Python3 interpreter
#    python checkout.py


REPOS = ['crane', 'pulp', 'pulp_docker', 'pulp_ostree', 'pulp_puppet', 'pulp_python', 'pulp_rpm']
BASE_DIR_TEMPLATE = '~/devel/%s'


def get_args():
    parser = argparse.ArgumentParser(description='Checkout your repos to a version of Pulp')
    parser.add_argument('--version', default='master', help='the version of Pulp to check out')
    parser.add_argument('--remote', default='pulp', help='the name of the pulp remote to fetch from')
    return parser.parse_args()


def get_yaml(args):
    url = "https://raw.githubusercontent.com/pulp/pulp_packaging/master/ci/config/releases/%s.yaml" % args.version
    r = requests.get(url)
    if r.status_code == 404:
        raise ValueError("Release config not found.")
    if r.status_code != 200:
        raise RuntimeError('An exception occured while fetching the release config')
    return yaml.load(r.text)


def check_checkouts(args):
    for repo in REPOS:
        checkout_path = os.path.expanduser(BASE_DIR_TEMPLATE % repo)
        if os.path.exists(checkout_path):
            try:
                subprocess.check_call(["git", "diff", "--exit-code"], cwd=checkout_path)
            except subprocess.CalledProcessError:
                print("\n\nThe repo '%s' has uncommitted changes. Either commit or revert those changes to continue.\n\nNo changes were made." % repo)
                sys.exit(1)


def fetch_and_checkout(args, yaml):
    for repo in REPOS:
        checkout_path = os.path.expanduser(BASE_DIR_TEMPLATE % repo)
        if os.path.exists(checkout_path):
            subprocess.check_call(["git", "fetch", args.remote], cwd=checkout_path)
            for entry in yaml['repositories']:
                if entry['name'] == repo:
                    subprocess.check_call(["git", "checkout", "%s/%s" % (args.remote, entry['git_branch'])], cwd=checkout_path)
            subprocess.call(["find", "./", "-name", "*.py[c0]", "-delete"], cwd=checkout_path)


def main():
    args = get_args()
    check_checkouts(args)
    yaml = get_yaml(args)
    fetch_and_checkout(args, yaml)


if __name__ == "__main__":
    main()
