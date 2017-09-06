#!/usr/bin/env python3
"""
This module gathers Pulp specific Ansible facts about the remote machine.
"""
import os

from ansible.module_utils.basic import AnsibleModule

# These lists can be defined anywhere in ansible; we could make it a passed-in arg if we wanted to.
# Since we return facts from this module based on these lists, for now they makes sense being here.

# plugin repository names, declared deparately from all repositories for easy filtering later
plugins = [
    'pulp_docker',
    'pulp_file',
    'pulp_ostree',
    'pulp_puppet',
    'pulp_python',
    'pulp_rpm',
]

# all repository names, used first to make sure the platform repository is cloned in its configured
# location, and then to generate filtered lists that can be used in task loops, to ensure we only
# loop over repos that exist when, e.g. creating virtualenvs and installing their requirements
repositories = [
    'pulp',
    'devel',
    'packaging',
    'crane',
    'pulp-smash',
    'pulpproject.org',
] + plugins

requirements_files = {
    'pulp': ['test_requirements.txt', 'dev_requirements.txt', 'docs/requirements.txt'],
    'crane': ['test-requirements.txt'],
    'pulp-smash': ['requirements.txt', 'requirements-dev.txt'],
}


def available_repositories(module):
    """Find the source code for the Pulp platform and its plugins."""
    _available_repositories = []
    try:
        repos = os.listdir(module.params['devel_dir'])
    except FileNotFoundError:
        repos = []
    for repo in repos:
        if (os.path.isdir(os.path.join(module.params['devel_dir'], repo)) and
                repo in repositories):
            _available_repositories.append(repo)
    return _available_repositories


def main():
    module = AnsibleModule(
        argument_spec={
            'devel_dir': {
                'required': True,
                'type': 'path',
            },
        },
        # since we don't make any changes when gather facts, this should be fine for check mode
        supports_check_mode=True
    )
    result = {}

    # All returned facts should be prepended with 'pulp_' for namespacing purposes,
    # and to make it clear that those facts were provided by this module.
    facts = {'pulp_available_repositories': available_repositories(module)}

    # filter the plugins list against the available repos to get available plugins
    facts['pulp_available_plugins'] = list(filter(lambda repo: repo in plugins,
                                                  facts['pulp_available_repositories']))

    # filter the requirements list against the available repos, removing unavailable repos
    facts['pulp_requirements_files'] = {
        k: v for k, v in requirements_files.items() if k in facts['pulp_available_repositories']
    }

    result['ansible_facts'] = facts

    module.exit_json(**result)


if __name__ == '__main__':
    main()
