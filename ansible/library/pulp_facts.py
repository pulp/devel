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

rpm_dependency_list = list(['acl', 'createrepo', 'createrepo_c', 'crontabs',
                            'deltarpm', 'genisoimage', 'git', 'gnupg', 'gofer',
                            'httpd', 'kobo', 'libmodulemd', 'libselinux-python',
                            'm2crypto', 'mod_ssl', 'mod_wsgi', 'mod_xsendfile',
                            'nss-tools', 'openssl', 'ostree', 'policycoreutils-python',
                            'puppet', 'pygobject3', 'pyliblzma', 'python', 'python-blinker',
                            'python-celery', 'python-debian', 'python-deltarpm', 'python-flask',
                            'python-gnupg', 'python-gofer', 'python-httplib2', 'python-iniparse',
                            'python-isodate', 'python-ldap', 'python-mongoengine',
                            'python-nectar', 'python-oauth2', 'python-okaara', 'python-pycurl',
                            'python-pymongo', 'python-qpid', 'python-semantic_version',
                            'python-setuptools', 'python-twine', 'python-twisted',
                            'python2-debpkgr', 'python2-django', 'python2-gnupg', 'python2-lxml',
                            'python2-solv', 'repoview', 'rsync', 'selinux-policy', 'systemd',
                            'yum'])

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
