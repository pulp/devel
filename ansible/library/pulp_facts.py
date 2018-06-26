#!/usr/bin/env python2
"""
This module gathers Pulp specific Ansible facts about the remote machine.
"""
import json
import os
import pwd
import subprocess


pipe = subprocess.Popen('/usr/bin/yum-config-manager pulp-nightlies', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
pulp_nightly_repo_enabled = 'enabled = True' in stdout

# Determine if selinux is Enforcing or not
pipe = subprocess.Popen('/usr/sbin/getenforce', stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=True)
stdout, stderr = pipe.communicate()
selinux_enabled = 'Enforcing' in stdout

rpm_dependency_list = list(['nss-tools', 'pygobject3', 'deltarpm', 'kobo', 'puppet',
                            'python2-lxml', 'python-ldap', 'crontabs', 'httpd', 'systemd', 'git',
                            'mod_ssl', 'python-pycurl', 'python-oauth2', 'policycoreutils-python',
                            'python-isodate', 'python-nectar', 'libselinux-python',
                            'python-blinker', 'python-iniparse', 'python-flask', 'mod_wsgi',
                            'repoview', 'python-mongoengine', 'python-setuptools',
                            'python2-django', 'python', 'python-deltarpm',
                            'rsync', 'pyliblzma', 'python-httplib2', 'm2crypto', 'genisoimage',
                            'createrepo', 'python-twisted', 'python-qpid', 'mod_xsendfile',
                            'python-twine', 'selinux-policy', 'python-pymongo', 'python-gnupg',
                            'gofer', 'ostree', 'python-semantic_version', 'openssl', 'acl',
                            'createrepo_c', 'yum', 'python-okaara', 'gnupg', 'python-gofer',
                            'python-celery', 'python-debian', 'python2-debpkgr', 'python2-gnupg'])

# Build the facts for Ansible
facts = {
    'ansible_facts': {
        'pulp_nightly_repo_enabled': pulp_nightly_repo_enabled,
        'selinux_enabled': selinux_enabled,
        'pulp_rpm_dependencies': rpm_dependency_list,
    }
}


# "return" the facts to Ansible
print json.dumps(facts)
