"""
This module contains helpful methods for release engineering tasks. This is what
drives the rel-eng related commands.
"""

import functools
import os
import re
import subprocess
import sys
import tempfile
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


def clean_config(config):
    """Remove keys that shouldn't be checked into source control"""
    for package in config['pulp-packages']:
        for key in package.copy():
            if key not in ('name', 'release', 'version', 'treeish'):
                del package[key]


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


def pulp_tarballs(config, packaging_repo):
    """
    Build tarballs for all the Pulp projects.

    Although we could use the archive feature of GitHub, it uses the prefix
    `<project-name>-<treeish>` which is painful to deal with in the specfile.
    This simply checks out the repository and calls `git archive` with the
    project name as the prefix. It also updates the configuration with the
    actual commit hash used when building from a treeish object.
    """
    # The approximate build time, used in the nightly Release field
    buildtime = time.strftime('%Y%m%d%H%M')

    for package in config['pulp-packages']:
        destination = os.path.join(packaging_repo, 'rpms/', package['name'].replace('_', '-'),
                                   'sources')
        package['url'] = 'https://github.com/pulp/{name}/'.format(name=package['name'])
        git_archive(package, destination_dir=destination)

        # This format loosely follows the Fedora guidelines, but uses hours and
        # minutes in the timestamp. In the case of nightly builds, the Release field
        # will use this format.
        package['snap_release'] = '0.1n' + buildtime + 'git' + package['commit'][0:7] + '%{?dist}'


def deps_tarballs(config, packaging_repo):
    """
    Fetch the source tarballs for all our dependencies using spectool.

    :param packaging_repo: path to the pulp/packaging repository.
    """
    for platform in config['platforms']:
        # Not all deps exist on every branch, so loop through them all
        checkout(platform)

        for package in config['external-deps']:
            name = package['name']
            base_dir = os.path.join(packaging_repo, 'rpms/{name}/'.format(name=name))
            source_dir = os.path.join(base_dir, 'sources/')
            specfile = os.path.join(base_dir, name + '.spec')

            if not os.path.exists(specfile):
                print(('Skipping {name} on {platform} since the specfile is missing from'
                       '{path}').format(name=name, platform=platform, path=specfile))
                continue

            os.makedirs(source_dir, exist_ok=True)
            command = "spectool -C {destination} -g {spec}".format(
                destination=source_dir, spec=specfile)
            print('Running "' + command + '"')
            subprocess.check_call(command, shell=True)


def git_archive(package, destination_dir):
    """
    Use Git to checkout the package source, build an archive using the project name as its
    archive prefix, and place it at the ``destination`` path.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        name = package['name'].replace('_', '-')
        destination = os.path.join(destination_dir, name + '-' + package['version'] + '.tar.gz')
        command = (
            'pushd {working_dir} && '
            'git clone {url} {name} && '
            'pushd {name} && '
            'git checkout {treeish} && '
            'echo "HEAD SHA1: $(git rev-parse HEAD)" && '
            'mkdir -p "$(dirname "{dest}")" && '
            'git archive --format=tar.gz --prefix={prefix}/ '
            '--output={dest} HEAD'
        )
        command = command.format(working_dir=tmp_dir, url=package['url'], name=name,
                                 prefix=name + '-' + package['version'],
                                 dest=destination, treeish=package['treeish'])

        print('\nRunning "' + command + '"\n')
        result = subprocess.check_output(command, shell=True)

        # Record the commit used for the tarball in the configuration
        for line in result.decode('utf8').split('\n'):
            if 'HEAD SHA1' in line:
                commit = line.split(':')[1].strip()
                break
        package['commit'] = commit


def build_srpms(config, spec_dir, package_names):
    packages = []
    if package_names:
        packages += filter(lambda p: p['name'] in package_names, config['pulp-packages'])
        packages += filter(lambda p: p['name'] in package_names, config['external-deps'])
    else:
        packages = config['pulp-packages'] + config['external-deps']

    for platform in config['platforms']:
        # The mock_root arch we choose to build the SRPM in shouldn't matter
        mock_root = config['platforms'][platform][0]
        checkout(platform)
        destination = os.path.join(os.getcwd(), 'SRPMS', platform)
        os.makedirs(destination, exist_ok=True)

        for package in packages:
            name = package['name'].replace('_', '-')
            base_dir = os.path.join(spec_dir, 'rpms/{dep}/'.format(dep=name))
            source_dir = os.path.join(base_dir, 'sources/')
            specfile = os.path.join(base_dir, name + '.spec')
            if not os.path.exists(specfile):
                print('Skipping {dep} on {platform} as the spec file is not present.'.format(
                    dep=name, platform=platform))
                continue

            if package['release'] == 'nightly':
                release = package['snap_release']
            else:
                release = package['release']
            set_release(specfile, release)
            set_version(specfile, package['version'])

            command = ("mock --no-clean -r {chroot} --buildsrpm --spec {spec} --sources"
                       " {source_dir} --resultdir {destination}")
            command = command.format(chroot=mock_root, spec=specfile, source_dir=source_dir,
                                     destination=destination)
            print('Running "' + command + '"')
            try:
                subprocess.check_output(command, shell=True)
            except subprocess.CalledProcessError as e:
                print('Failed to build SRPM: \n' + str(e.output))


def build_rpms(config_path, srpm_dir, dest=None, platforms=None, package_names=None, copr=False):
    """Build RPMs in either mock roots or Copr."""
    config = load_config(config_path)
    packages = []
    if package_names:
        packages += filter(lambda p: p['name'] in package_names, config['pulp-packages'])
        packages += filter(lambda p: p['name'] in package_names, config['external-deps'])
    else:
        packages = config['pulp-packages'] + config['external-deps']

    platforms = config['platforms'] if platforms is None else platforms

    for platform in platforms:
        platform_srpm_dir = os.path.join(srpm_dir, platform)
        platform_rpm_dir = os.path.join(dest, platform)
        os.makedirs(platform_rpm_dir, exist_ok=True)

        chroots = config['platforms'][platform]

        if copr:
            # Loop over SRPMs for each platform
            pass
        else:
            for package in packages:
                mock_rpm(chroots, platform_srpm_dir, platform_rpm_dir, package, config)


def copr_rpm(chroots, srpm_dir, package, config):
    pass


def mock_rpm(chroots, srpm_dir, rpm_dir, package, config):
    """Build an RPM with Mock, installing RPMs specified in the config"""
    install_command = "mock -r {chroot} -i {rpms}"
    build_command = ("mock --no-clean -r {chroot} --resultdir {destination} {srpm}")

    srpms = [f for f in os.listdir(srpm_dir) if f.endswith('src.rpm')]
    package_prefix = package['name'] + '-' + package['version']
    srpm = [os.path.join(srpm_dir, p) for p in srpms if
            p.startswith(package_prefix) and p.endswith('src.rpm')]
    if srpm:
        for chroot in chroots:
            # Unfortunately, some of our deps BuildRequire other deps we carry
            # so we have to install some previously built RPMs into the mock root.
            try:
                rpms = [f for f in os.listdir(rpm_dir) if
                        f.endswith('rpm') and not f.endswith('src.rpm')]
                build_required_rpms = [os.path.join(rpm_dir, rpm) for rpm in rpms if
                                       rpm.startswith(tuple(config['buildrequires']))]
                rpm_string = ' '.join(build_required_rpms)
                if build_required_rpms:
                    install_command = install_command.format(chroot=chroot, rpms=rpm_string)
                    print('Running "' + install_command + '"')
                    subprocess.check_output(install_command, shell=True)
            except subprocess.CalledProcessError as e:
                print('Failed to install RPMs: \n' + str(e.output))

            try:
                build_command = build_command.format(chroot=chroot, destination=rpm_dir,
                                                     srpm=srpm[0])
                subprocess.check_output(build_command, shell=True)
            except subprocess.CalledProcessError as e:
                print('Failed to build RPM: \n' + str(e.output))
                sys.exit(1)
    else:
        print('Skipping {pkg} since no SRPM is present'.format(pkg=package['name']))
