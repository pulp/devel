configure-rhel-7
================

Prepare the target RHEL 7 host for Pulp 3.

Specifically, do the following:

* Register and subscribe the host with subscription-manager. If registration
  information has changed, configure which repositories are enabled.
* Install the Python 3.6 SCL.

The following variables may be specified:

* *`rhn_pool`* A regular expression naming a pool, e.g. `'^SKU Name$'`.
* *`rhn_username`* A username for registering the host.
* *`rhn_password`* A password for registering the host.

Sample playbook:

```yaml
- hosts: all
  vars:
    ansible_python_interpreter: "/usr/bin/python2"
  vars_files:
    - ~/Documents/rhn-credentials.yml
  roles:
    - configure-rhel-7
```
