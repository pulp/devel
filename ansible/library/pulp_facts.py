#!/usr/bin/env python2
"""
This module gathers Pulp specific Ansible facts about the remote machine.
"""
import json
import os
import platform
import pwd
import shutil
import subprocess
import tempfile


pipe = subprocess.Popen('/usr/bin/yum-config-manager pulp-nightlies', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
pulp_nightly_repo_enabled = 'enabled = True' in stdout

# Determine if selinux is Enforcing or not
pipe = subprocess.Popen('/usr/sbin/getenforce', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
selinux_enabled = 'Enforcing' in stdout

# Determine the list of RPM dependencies
projects = [
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
rpm_dependency_list = []
# This is run using sudo, but the code is checked out in the normal user directory.
user_homedir = pwd.getpwuid(int(os.environ['SUDO_UID'])).pw_dir

# Figure out the platform and checkout the packaging repository branch
platform_dist = platform.linux_distribution()
if platform_dist[0].lower() == 'fedora':
    # Maybe we'll support other platforms for development, but right now Fedora is
    # all we work with.
    branch = 'f' + str(platform_dist[1])
else:
    raise OSError(str(platform_dist) + ' is not a supported development platform')

tmpdir = tempfile.mkdtemp()
git_clone = ('git clone -b {branch} --single-branch https://git@github.com/pulp/'
             'packaging.git {path}'.format(branch=branch, path=tmpdir))
proc = subprocess.Popen(git_clone, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = proc.communicate()

for project in projects:
    project_path = os.path.join(tmpdir, 'rpms/', project)
    if os.path.isdir(project_path):
        # Determine the dependencies by inspecting the 'Requires' in each spec file.
        # The results are then filtered to only include packages not provided by Pulp.
        rpmspec_command = r"rpmspec -q --queryformat '[%{REQUIRENEVRS}\n]' " + project_path + \
                          '/*.spec' + r'| grep -v "/.*" | grep -v "python-pulp.*" | ' \
                          r'grep -v "^pulp.*"'
        proc = subprocess.Popen(rpmspec_command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, shell=True)
        stdout, stderr = proc.communicate()
        rpm_dependency_list += [rpm.split()[0] for rpm in stdout.splitlines()]

shutil.rmtree(tmpdir)

# Remove any duplicates
rpm_dependency_list = set(rpm_dependency_list)

# XXX Temporary handling of the python-twisted -> python2-twisted rename
#     This needs to be fixed in the spec files, but the code above is reading
#     the wrong specfiles.
if 'python-twisted' in rpm_dependency_list:
    rpm_dependency_list.remove('python-twisted')
    rpm_dependency_list.add('python2-twisted')

# Build the facts for Ansible
facts = {
    'ansible_facts': {
        'pulp_nightly_repo_enabled': pulp_nightly_repo_enabled,
        'selinux_enabled': selinux_enabled,
        'pulp_rpm_dependencies': list(rpm_dependency_list),
    }
}


# "return" the facts to Ansible
print json.dumps(facts)
