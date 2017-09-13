Pulp User
=========

This role creates and customizes a user account that can host and run certain
Pulp 3 components.

Pulp 3 requires several components to act in concert. Some of these components
are installed system-wide, such as a relational database and an AMQP broker.
Other components can be installed into a Python virtualenv. This role creates
and customizes a user account that can host the virtualenv-based components, and
it exports several (per-host) useful variables.

Example Usage
-------------

```yaml
- hosts: all
  roles:
    - pulp-user
```

Variables
---------

The variables that this role uses, along with their default values, are listed
below:

```yaml
# The strategy to use when creating and configuring this user, and when
# installing Pulp and its plugins. If "pypi," perform the minimum tasks needed
# to create a functional Pulp installation. If "development," install code from
# source in editable mode, install extra dependencies, install Bash aliases,
# etc. If some other value, raise an error.
pulp_install_strategy: pypi

# The user that will host Pulp virtualenvs. This should be a dedicated user due
# to security concerns. This user's home directory is made world-readable, among
# other things.
pulp_user: pulp
```

This role exports the following facts (per-host variables):

* `pulp_user_home` The path to the pulp user's home directory.
* `pulp_devel_dir` The directory where git clones of code should exist.
* `venv_dir` The directory in which virtualenvs should be created.
* `pulp_venv` The name of the virtualenv in which Pulp should be installed.
* `pulp_smash_venv` The directory in which Pulp Smash should be installed.
