"""Utility functions for build scripts"""

import functools
import os
import re
import subprocess
import time
import yaml


def load_config(path):
    print('Loading config from ' + path)
    with open(path) as f:
        return yaml.load(f)


def write_config(path, config):
    """Write the configuration as a YAML file at the given path"""
    print('Writing updated configuration to ' + path)
    with open(path, 'w') as fp:
        yaml.dump(config, fp, default_flow_style=False)


def checkout(platform):
    """
    Checkout the platform branch in the packaging submodule. Note that this tosses
    any modified spec files in the packaging submodule.
    """
    packaging_path = os.path.join(os.getcwd(), 'packaging')
    subprocess.check_call('pushd {path} && git checkout -- . && git checkout {platform} && '
                          'popd'.format(path=packaging_path, platform=platform), shell=True)


def set_spec_field(field, specfile, new_value):
    """
    Set a specfile field.

    This is not a great solution, but I can't find the tool to set a field
    in a specfile.

    :param specfile: path to the specfile
    :param version:  a string to place in the version field
    """
    regex = re.compile('^({field}:\s*)(.+)$'.format(field=field), re.IGNORECASE)
    with open(specfile, 'r+') as spec_fp:
        spec = spec_fp.readlines()
        spec_fp.seek(0)

        for line in spec:
            match = re.match(regex, line)
            if match:
                line = ''.join((match.group(1), new_value, '\n'))
            spec_fp.write(line)


set_version = functools.partial(set_spec_field, 'Version')
set_release = functools.partial(set_spec_field, 'Release')


def clean_config(config):
    for package in config['pulp-packages']:
        try:
            del package['commit']
        except KeyError:
            pass
        try:
            del package['snap_release']
        except KeyError:
            pass
