#!/usr/bin/env python3
"""
This module gathers Pulp specific Ansible facts about the remote machine.
"""
import os
import platform
import subprocess
import tempfile

from ansible.module_utils.basic import AnsibleModule

# These lists can be defined anywhere in ansible; we could make it a passed-in arg if we wanted to.
# Since we return facts from this module based on these lists, for now they makes sense being here.

# name of RPMs, used to build a list of packages that they depend on
rpm_projects = [
    'crane',
    'pulp',
    'pulp-deb',
    'pulp-docker',
    'pulp-openstack',
    'pulp-ostree',
    'pulp-puppet',
    'pulp-python',
    'pulp-rpm'
]

# plugin repository names, declared deparately from all repositories for easy filtering later
plugins = [
    'pulp_puppet',
    'pulp_rpm',
    'pulp_docker',
    'pulp_ostree',
    'pulp_python',
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

# lists of requirements files to be installed into virtualenvs, when those virtualenvs exist
# all requirements found in a given repository matching these filenames will be installed into
# the corresponding virtualenvs using code from that repository
requirements_files = {
    'pulp': ['test_requirements.txt', 'dev_requirements.txt'],
    'crane': ['test-requirements.txt'],
    'pulp-smash': ['requirements.txt', 'requirements-dev.txt'],
}


def nightly_repo_enabled():
    # Determine if the "pulp-nightlies" repo is enabled or not
    pipe = subprocess.Popen('/usr/bin/yum-config-manager pulp-nightlies', stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=True)
    stdout, stderr = pipe.communicate()
    return 'enabled = True' in stdout.decode('utf8')


def selinux_enforcing():
    # Determine if selinux is Enforcing or not
    pipe = subprocess.Popen('/usr/sbin/getenforce', stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=True)
    stdout, stderr = pipe.communicate()
    return 'Enforcing' in stdout.decode('utf8')


def rpm_dependencies(module):
    # Determine RPM dependencies by inspecting the 'Requires' in each spec file.
    # The results are then filtered to only include packages not provided by Pulp.
    rpm_dependencies = set()

    # Figure out the packaging repository branch to use for rpm specs based on platform
    platform_dist = platform.linux_distribution()
    if platform_dist[0].lower() == 'fedora':
        # right now Fedora is the only supported platform
        branch = 'f' + str(platform_dist[1])
    else:
        msg = '{} is not a supported development platform'.format(platform_dist)
        module.fail_json(msg=msg, name=platform_dist)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            git_clone = ('git clone -b {branch} --single-branch https://git@github.com/pulp/'
                         'packaging.git {path}'.format(branch=branch, path=tmpdir))
            proc = subprocess.Popen(git_clone, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, shell=True)
            stdout, stderr = proc.communicate()

            for project in rpm_projects:
                project_path = os.path.join(tmpdir, 'rpms/', project)
                if os.path.isdir(project_path):
                    # Use rpmspec to get all the required package NEVRs. Then use grep -v to remove
                    # pulp and pulp-related packages. Use awk to only print the first field, which
                    # is the name of the required non-pulp package.
                    rpmspec_pipechain = [
                        "rpmspec -q --queryformat '[%{REQUIRENEVRS}\n]' {}/*.spec | ",
                        'grep -v "/.*"',
                        'grep -v "python-pulp.*"',
                        'grep -v "^pulp.*"',
                        "awk '{ print $1 }'"
                    ]
                    rpmspec_command = ' | '.join(rpmspec_pipechain)
                    proc = subprocess.Popen(rpmspec_command, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, shell=True)
                    stdout, stderr = proc.communicate()
                    for line in stdout.decode('utf8').splitlines():
                        rpm_dependencies.add(line)
    except FileNotFoundError:
        # In fedora 25, the __exit__ method of the tmpdir context manager fails, because the tmp
        # dir doesn't exist when it tries to delete it (?!)
        pass

    return list(rpm_dependencies)


def available_repositories(module):
    # determine which of the platform and plugin are available,
    # failing if platform is not available
    available_repositories = []

    try:
        repos = os.listdir(module.params['devel_dir'])
    except FileNotFoundError:
        repos = []

    for dirname in repos:
        if os.path.isdir(os.path.join(module.params['devel_dir'], dirname)):
            if dirname in repositories:
                available_repositories.append(dirname)

        # if the dirname is pulp, and it doesn't pass the isdir check, there's no
        # platform repository in the expected location. Time to explode.
        elif dirname == 'pulp':
            msg = ('pulp repo not found in {} on remote machine, '
                   'unable to proceed'.format(module.params['devel_dir']))
            module.fail_json(name='pulp', msg=msg)
    return available_repositories


def created_virtualenvs(module):
    # Determine what virtualenvs have already been created, for skipping
    created_virtualenvs = []

    try:
        venvs = os.listdir(module.params['venv_dir'])
    except FileNotFoundError:
        venvs = []

    for dirname in venvs:
        if (os.path.isdir(os.path.join(module.params['venv_dir'], dirname)) and
                dirname in repositories):
            created_virtualenvs.append(dirname)
    return created_virtualenvs


def main():
    module = AnsibleModule(
        argument_spec={
            'devel_dir': {
                'required': True,
                'type': 'path',
            },
            'venv_dir': {
                'required': True,
                'type': 'path',
            }
        },
        # since we don't make any changes when gather facts, this should be fine for check mode
        supports_check_mode=True
    )
    result = {}

    # All returned facts should be prepended with 'pulp_' for namespacing purposes,
    # and to make it clear that those facts were provided by this module.
    facts = {
        'pulp_nightly_repo_enabled': nightly_repo_enabled(),
        'pulp_selinux_enforcing': selinux_enforcing(),
        'pulp_rpm_dependencies': rpm_dependencies(module),
        'pulp_available_repositories': available_repositories(module),
        'pulp_created_virtualenvs': created_virtualenvs(module),
    }

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
