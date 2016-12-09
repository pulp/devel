Pulp Development Repository
===========================

This repository contains various tools that are useful for developing Pulp.

Complete documentation for using the repository can be found in
[the contributing guide](https://docs.pulpproject.org/en/3.0/nightly/contributing/dev-setup.html)

Ansible
-------

A collection of Ansible roles and playbooks that deploy Pulp and its
dependencies.


Vagrantfile
-----------

Uses a pre-made image and our ansible playbook to deploy a pulp development environment.


rel-eng
-------

Release engineering tools and configuration. This includes tools to interact
with the packaging files in https://github.com/pulp/packaging.


scripts
-------

A collection of shell scripts useful to Pulp development.


pulp-dev
--------

A Python package for Pulp development. This package provides various libraries
and command line tools.
