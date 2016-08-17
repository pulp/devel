"""
This module contains helpful methods for release engineering tasks. This is what
drives the rel-eng related commands.
"""

import fnmatch
import functools
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict

import copr
import rpm
import yaml

# used to extract version and release components from an RPM-style EVR string (NEVRA without NA)
EVR_VERSION_RE = '(?P<epoch>\d+)?(?:\:?)(?P<major>\d+)\.(?P<minor>\d+)(?:\.?)(?P<patch>\d+)?'
EVR_RELEASE_RE = '(?P<major>\d+)(?:\.?)(?P<minor>\d+)?(?:\.?)(?P<stage>.+[^.])?'

# regexen for replacing version strings in pyfiles
_PY_RE_BASE = "(\s*)({param})(\s*)(=)(\s*)(['\"])(.*)(['\"])(.*)"
PY_VERSION_RE = _PY_RE_BASE.format(param='version')
PY_RELEASE_RE = _PY_RE_BASE.format(param='release')


@functools.total_ordering
class EVR(object):
    _PYTHON_STAGE_MAP = {'alpha': 'a', 'beta': 'b', 'rc': 'rc'}

    def __init__(self, version, release, commit_hash=None):
        self.commit = commit_hash
        # sometimes these are ints or floats when parsing from yaml
        # nudge them back into strings rather than punishing the user with a cryptic TypeError
        version, release = str(version), str(release)

        if release == 'nightly':
            if self.commit is None:
                raise ValueError('Cannot create nightly EVR without commit hash.')
            else:
                # replace "nightly"/"scratch" with a real release string
                # according to our nightly format
                release = self._build_nightly_release()

        try:
            self.epoch, self.v_major, self.v_minor, self.v_patch = self.parse_version(version)
            self.r_major, self.r_minor, self.r_stage = self.parse_release(release)
        except AttributeError:
            # Exception handling might be too wide, but is based on the thinking that a match
            # failure will result in a method call on none (e.g. match.groups() where match
            # is None), which AttributeErrors.
            errmsg = ('Invalid version string. Expecting "x.y.z-release.\n'
                      'Got version "{}" and release "{}".').format(version, release)
            raise ValueError(errmsg)

    @classmethod
    def fromstring(cls, evr_string):
        version, release = evr_string.rsplit('-', 1)
        return cls(version, release)

    @classmethod
    def lowest(cls):
        return cls('0.0', '0')

    def __eq__(self, other):
        # For equality, delegate out to the string method, since it normalizes versions
        # As a side-effect, this means you can (usually) compare EVR objects to EVR strings
        if str(self) == str(other):
            return True

    def __lt__(self, other):
        # total_ordering decorator uses this and __eq__ to define the rich comparators
        for component in ('epoch', 'v_major', 'v_minor', 'v_patch', 'r_major', 'r_minor'):
            # compare the int components directly, returning as soon as possible
            # this should handle almost all cases, except comparing two releases with
            # the same release major and minor numbers, which should never happen except
            # in the case of nightlies.
            if getattr(self, component) < getattr(other, component):
                return True

        # need special handling for stage since it can be None or nightly
        if self.r_stage != other.r_stage:
            if self.r_stage is None:
                # current stage is None (released), other is lesser
                # this should never happen, since different stages should have
                # different r_major and r_minor numbers, but it's supported
                return False
            elif other.r_stage is None:
                # current stage is *not* None, other is greater
                # this should also never happen, for the same reason
                return True
            # Nones are accounted for at this point, so we can start with string compares
            elif self.r_stage[0] == 'n' and not other.r_stage[0] == 'n':
                # self is a nightly, other is not, self is lesser
                # again, should never happen since nightlies have r_major and r_minor of 0,
                # but it's supported
                return True
            elif other.r_stage[0] == 'n' and not self.r_stage[0] == 'n':
                # other is a nightly, self is not, self is not lesser
                return False
            # Nones and nightlies are accounted for now, so we can do normal string compare
            else:
                # 'alpha' < 'beta' < 'rc' is True
                # nightly strings are made to compare as strings.
                return self.r_stage < other.r_stage

        # The versions are equal.
        return False

    def __hash__(self):
        evr_hash = hashlib.sha1(str(self))
        return int(evr_hash.hexdigest(), 16)

    def _build_nightly_release(self):
        # This format loosely follows the Fedora guidelines, but uses hours and
        # minutes in the timestamp. In the case of nightly builds, the Release field
        # will use this format.
        buildtime = time.strftime('%Y%m%d%H%M')
        return '0.0.n' + buildtime + 'git' + self.commit[0:7]

    @property
    def version(self):
        version = '{}.{}.{}'.format(self.v_major, self.v_minor, self.v_patch)
        if self.epoch:
            return '{}:{}'.format(self.epoch, version)
        else:
            return version

    @property
    def release(self):
        if self.r_stage:
            release = '{}.{}.{}'.format(self.r_major, self.r_minor, self.r_stage)
        else:
            if self.r_minor:
                release = '{}.{}'.format(self.r_major, self.r_minor)
            else:
                release = str(self.r_major)
        return release

    @property
    def dist_release(self):
        # nothing fancy, just the release component plus the dist macro for use in spec files
        return self.release + '%{?dist}'

    @property
    def nightly_release(self):
        if self.r_stage and self.r_stage[0] == 'n':
            return True
        else:
            return False

    @property
    def tagged_release(self):
        # bool indicating whether or not this is a release that should be tagged, based on
        # the release component. Nightlies are not tagged, all other builds should be.
        return not self.nightly_release

    @property
    def python_version(self):
        # using nick coghlan's rules: https://www.python.org/dev/peps/pep-0440/
        # - [epoch!]v_major(.v_minor[.v_patch])*[{a|b|rc}N][.postN][.devN]
        # short version:
        # - epoch is separated by !, not : (default 0 is still left off)
        # - 1.2.0 == 1.2, so if patch is 0, leave it out
        # - release has some special rules, best demonstrated by examples
        #   - 1.2.3-0.0.n(nightly_date_string) => 1.2.3.dev(nightly_date_string)
        #   - 1.2.3-0.1.alpha => 1.2.3a1 -- only integer pre-release numbers are supported,
        #     so drop the release major number and only use the release minor number
        #   - 1.2.3-0.2.alpha => 1.2.3a2
        #   - 1.2.3-0.4.beta => 1.2.3b4 -- don't reset minor release counter when advancing
        #     to the next stage to keep the RPM and python versions interchangeable
        #   - 1.2.3-0.5.rc => 1.2.3rc5
        #   - 1.2.3-1 => 1.2.3 -- release of -1 is the first and likely only GA release
        # - it's probably best if we never need to do stuff like this:
        #   - 1.2.3-2 => 1.2.3post2
        #   - 1.2.3-3.1 => nope! -- only integer post-release numbers are supported,
        #     so the minor number will be ignored (i.e. don't do this)
        #   - 1.2.3-1.1.beta => nope! -- While PEP0440 supports post-releases of pre-releases,
        #     like 1.2.3a1.post2, it does not support pre-releases of post-releases.
        #     No strategy for handling this case exists, and this should never happen since
        #     a failure in packaging normally results in a hotfix patch release.
        #     In short: don't make prerelease RPMs with a release major number of 1 or higher.

        version = self.version.replace(':', '!')
        # if patch is 0, take off the trailing '.0'
        if self.v_patch == 0:
            version = version[:-2]

        # the release-based suffix is a little more complicated
        if self.r_stage:
            if self.nightly_release:
                # nightly build, construct a 'dev' string, strip off the leading 'n'
                version += 'dev' + self.r_stage[1:]
            else:
                # normal release stage
                # if we have a release stage, convert the stage to its python value and append
                # only the release minor number, since the major number must be zero
                version += (self._PYTHON_STAGE_MAP[self.r_stage] + str(self.r_minor))
        elif self.r_major > 1:
            # otherwise, use the major number, since it must be greater than 1
            version += '.post{}'.format(self.r_major)
        return version

    def __str__(self):
        return '-'.join((self.version, self.release))

    def __repr__(self):
        return '<{}: {}>'.format(type(self).__name__, str(self))

    def copy(self):
        return type(self)(self.version, self.release)

    def parse_version(self, version):
        # split an rpm version string into epoch, major, minor, patch
        # expects an rpm-style evr string, e.g. 0:1.2.3-release0 (epoch and colon optional)
        # package name and arch should be excluded
        epoch, major, minor, patch = re.match(EVR_VERSION_RE, version).groups()
        if epoch is None:
            epoch = 0
        if patch is None:
            patch = 0
        return (int(x) for x in (epoch, major, minor, patch))

    def parse_release(self, release):
        # split an rpm release component into major, minor, stage, e.g. '0.1.alpha'
        # becomes (0, 1, alpha). '1' would become (1, None, None).
        # Released RPMs do not have a stage.
        # Passing in the special 'nightly' value for release will construct a nightly release
        # component.
        if release == 'nightly':
            release = self.nightly_release

        major, minor, stage = re.match(EVR_RELEASE_RE, release).groups()
        major = int(major)
        if minor is None:
            minor = 0
        if stage and major != '0':
            if stage in self._PYTHON_STAGE_MAP:
                # This is due to the python versioning rules.
                raise ValueError('Release major version must be 0 if stage is not release.')
        elif not stage and major < 1:
            raise ValueError('Release major version must be greater than 0 if stage is release.')
        return int(major), int(minor), stage

    def next_stage(self):
        # return the next stage for this EVR: alpha -> beta -> rc > None (GA release)
        if self.r_stage is None or self.r_stage.startswith('n'):
            next_stage = 'alpha'
        elif self.r_stage == 'alpha':
            next_stage = 'beta'
        elif self.r_stage == 'beta':
            next_stage = 'rc'
        elif self.r_stage == 'rc':
            next_stage = None  # GA release
        else:
            raise ValueError('Unknown self.r_stage: {}'.format(self.r_stage))
        return next_stage

    # XXX holy bejeebus this needs unit tests
    def increment(self, major=False, minor=False, patch=False, release=False,
                  stage=False, next_stage=None):
        """Increment a component of this version according to Pulp versioning rules.

        Returns a new EVR instance, does not increment in-place.

        Given this EVR string: "1.2.3-0.1.beta", the major version component is "1", the minor
        version component is "2", the patch version component is "3". The release component is
        "0.1.beta", made up of release major component "0", release minor component "1", and
        release stage "beta".

        Unless stage is True or next_stage is set, the release stage will not advance through the
        "alpha" -> "beta" -> "rc" -> "ga" cycle. Before GA, the major release component will
        always be 0, and the minor release component will be incremented. Upon moving to GA, the
        release minor component and stage will be ignored, and only the release major component
        will be incremented.

        Incrementing the epoch is not supported.

        :param major: Increment the major version component
        :param minor: Increment the minor release component
        :param patch: Increment the patch release component
        :param release: Increment to next release stage with appropriate release version
        :param stage: Increment to next stage
        :param next_stage: Force stage in incremented version to this stage (release minor
                           component will be incremented)

        """
        copy = self.copy()

        # If a next stage was passed in, use it. If not, calculate the next stage if "stage" is
        # going to be incremented, otherwise just use the current stage.
        # next_stage will remain None if the next stage is GA, or release is True
        if next_stage is None:
            if stage:
                next_stage = copy.next_stage()
            elif release:
                next_stage = None
            else:
                next_stage = copy.r_stage

        # fun failsafe: if next_stage is still None at this point, release gets forced to
        # True, since that's what a next_stage of None means.
        if next_stage is None:
            release = True

        if any((major, minor, patch)):
            # anything updating the version gets a new release value: 0.1.<stage>
            # unless release is True, then update the release major and reset release minor
            if release:
                copy.r_major = 1
                copy.r_minor = 0
            else:
                copy.r_major = 0
                copy.r_minor = 1
            copy.r_stage = next_stage

        if major:
            # 1.2.3 becomes 2.0.0
            copy.v_major += 1
            copy.v_minor = copy.v_patch = 0
        elif minor:
            # 1.2.3 becomes 1.3.0
            copy.v_minor += 1
            copy.v_patch = 0
        elif patch:
            # 1.2.3 becomes 1.2.4
            copy.v_patch += 1
        elif next_stage:
            # always increment the minor release if advancing to a non-release stage
            copy.r_major = 0
            copy.r_minor += 1
            if stage:
                copy.r_stage = next_stage

        return copy


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
    for package, package_config in config['pulp-packages'].items():
        for key in package_config.copy():
            if key not in ('release', 'version', 'treeish'):
                del package_config[key]


def checkout(platform):
    """
    Checkout the platform branch in the packaging submodule. Note that this tosses
    any modified spec files in the packaging submodule.
    """
    packaging_path = os.path.join(os.getcwd(), 'packaging')

    # XXX: Branch names should match dist values. Until we decide to rename them (or not?)...
    if platform.startswith('fc'):
        platform = platform.replace('fc', 'f')

    subprocess.check_call('pushd {path} && git checkout -- . && git checkout {platform} && '
                          'popd'.format(path=packaging_path, platform=platform), shell=True)


def update_python_versions(py_source_dir, evr):
    # Update the py files likely to have versions in them (setup.py, package __init__.py)
    replace_version_in_files(py_source_dir, 'setup.py', evr.python_version, PY_VERSION_RE)
    replace_version_in_files(py_source_dir, '__init__.py', evr.python_version, PY_VERSION_RE)

    # also update the docs config
    # http://www.sphinx-doc.org/en/stable/config.html#confval-version
    # These are both set to evr.python_version so the generated docs are
    # always clear about the docs state regardless of which macro gets used
    replace_version_in_files(py_source_dir, 'conf.py', evr.python_version, PY_VERSION_RE)
    replace_version_in_files(py_source_dir, 'conf.py', evr.python_version, PY_RELEASE_RE)


def set_spec_field(field, specfile, new_value):
    """
    Set a specfile field.

    This is not a great solution, but I can't find the tool to set a field
    in a specfile.

    :param specfile: path to the specfile
    :param version:  a string to place in the version field
    """
    regex = re.compile('^({field}:\s*)(.+)$'.format(field=field), re.IGNORECASE)
    with open(specfile, 'r') as spec_fp:
        spec_lines = spec_fp.readlines()

    with open(specfile, 'w') as spec_fp:
        for line in spec_lines:
            match = re.match(regex, line)
            if match:
                line = ''.join((match.group(1), new_value, '\n'))
            spec_fp.write(line)


set_spec_version = functools.partial(set_spec_field, 'Version')


set_spec_release = functools.partial(set_spec_field, 'Release')


def set_spec_evr(specfile, evr):
    set_spec_version(specfile, evr.version)
    set_spec_release(specfile, evr.release)


def get_spec_version(specfile):
    """
    Return the version from the spec

    :param specfile: The path to a spec file
    :type specfile: str
    :return: spec version
    :rtype: str
    """
    # Get the dep name & version
    spec = rpm.spec(specfile)
    # XXX For unknown reasons, sourceHeader sometimes returns a python
    #     repr of the release string bytes, rather than the string itself,
    #     e.g. literally "b'version'" when it should just be "version".
    return str(spec.sourceHeader[rpm.RPMTAG_VERSION]).strip("b'")


def get_spec_release(specfile):
    """
    Return the release from a spec file

    :param specfile: The path to a spec file
    :type specfile: str
    :return: spec release without the dist macro
    :rtype: str
    """
    # Get the dep name & version
    spec = rpm.spec(specfile)
    release = str(spec.sourceHeader[rpm.RPMTAG_RELEASE]).strip("b'")
    print(release)
    # split the dist from the end of the nvr
    release = str(release).rsplit('.')[0]
    return release


def get_spec_evr(specfile):
    """
    Return an EVR object based on a specfile's version and release

    :param spectfile: The path to a spec file
    :type specfile: str
    :return: EVR object based on the specfile contents
    :rtype: pulp_dev.releng_utils.EVR
    """
    version = get_spec_version(specfile)
    release = get_spec_release(specfile)
    return EVR(version, release)


def pulp_tarballs(config, packaging_repo, clean=False):
    """
    Build tarballs for all the Pulp projects.

    Although we could use the archive feature of GitHub, it uses the prefix
    `<project-name>-<treeish>` which is painful to deal with in the specfile.
    This simply checks out the repository and calls `git archive` with the
    project name as the prefix. It also updates the configuration with the
    actual commit hash used when building from a treeish object.
    """
    for name, package in config['pulp-packages'].items():
        destination = os.path.join(packaging_repo, 'rpms/', name.replace('_', '-'),
                                   'sources')
        git_archive(name, package, package['version'], package['release'],
                    destination_dir=destination, clean=clean)


def deps_tarballs(config, packaging_repo):
    """
    Fetch the source tarballs for all our dependencies using spectool.

    :param packaging_repo: path to the pulp/packaging repository.
    """
    for platform in config['platforms']:
        # Not all deps exist on every branch, so loop through them all
        checkout(platform)

        for name, package in config['external-deps'].items():
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


def git_tag_commit(git_directory, evr, platform=None):
    """Tag a new commit to a git repo with the given version and release"""
    # evr can be an EVR instance or string; it is cast to string here
    evr = str(evr)
    if platform is not None:
        # if given a platform, prepend it to the evr
        # this lets us tag per-platform for the spec files in the packaging repo
        evr = '-'.join((platform, evr))

    # XXX Add confirmation here until this stuff actually works.
    if not input('Tag {} with {}? "y" to do it.'.format(git_directory, evr)).lower() == 'y':
        print('Skipping tag {}.')
        return

    command = (
        'git commit -m "Tagging version {evr}" && '
        'git tag {evr} HEAD && '
        'echo git push --tags origin'
    ).format(evr=evr)
    # fails if this version is already tagged, hopefully preventing duplicate nevra in copr
    subprocess.check_call(command, cwd=git_directory, shell=True)


def git_archive(name, package, version, release, destination_dir, clean=False):
    """
    Use Git to checkout the package source, build an archive using the project name as its
    archive prefix, and place it at the ``destination`` path.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # this get used with an rm -rf operation, so strip off slashes to prevent badness
        basename = name + '-' + version
        destination = os.path.join(destination_dir, basename + '.tar.gz')
        if clean:
            # strip off slashes as a minimum safety for rm -rf
            command = 'rm -rf {name} && '.format(name=name.strip('/'))
        else:
            command = ''

        command += (
            'git clone {url} {name} && '
            'pushd {name} && '
            'git checkout {treeish} && '
            'popd'
        ).format(url=package['url'], name=name, treeish=package['treeish'])
        print('\nRunning "' + command + '"\n')
        result = subprocess.check_output(command, shell=True)

        command = (
            'pushd {name} && '
            'echo "HEAD SHA1: $(git rev-parse HEAD)" && '
            'popd'
        ).format(name=name)
        result = subprocess.check_output(command, shell=True)

        # Record the commit used for the tarball in the configuration
        for line in result.decode('utf8').split('\n'):
            if 'HEAD SHA1' in line:
                commit = line.split(':')[1].strip()
                break
        package['commit'] = str(commit)

        evr = EVR(version, release, commit_hash=package['commit'])

        if evr.nightly_release:
            print('Updating python files with nightly version string')
            update_python_versions(tmp_dir, evr)
            package['snap_release'] = evr.release

        command = (
            'pushd {name} && '
            'mkdir -p "$(dirname "{dest}")" && '
            'git archive --format=tar.gz --prefix={prefix}/ '
            '--output={dest} HEAD &&'
            'popd'
        ).format(name=name, dest=destination, prefix=basename)

        print('\nRunning "' + command + '"\n')
        result = subprocess.check_output(command, shell=True)

        for line in result.decode('utf8').split('\n'):
            if 'HEAD SHA1' in line:
                commit = line.split(':')[1].strip()
                break


def build_srpms(config, spec_dir, package_names=None, clean=False):
    combined = list(config['pulp-packages'].items()) + list(config['external-deps'].items())
    if package_names:
        packages = {}
        for name, package in combined:
            if name in package_names:
                packages[name] = package
    else:
        packages = dict(combined)

    for platform in config['platforms']:
        # The mock_root arch we choose to build the SRPM in shouldn't matter
        mock_root = config['platforms'][platform][0]
        checkout(platform)
        destination = os.path.join(os.getcwd(), 'SRPMS', platform)
        if clean:
            subprocess.call('rm -rf {}'.format(destination), shell=True)
        os.makedirs(destination, exist_ok=True)

        for name, package in packages.items():
            base_dir = os.path.join(spec_dir, 'rpms/{dep}/'.format(dep=name))
            source_dir = os.path.join(base_dir, 'sources/')
            specfile = os.path.join(base_dir, name + '.spec')
            if not os.path.exists(specfile):
                print('Skipping {dep} on {platform} as the spec file is not present.'.format(
                    dep=name, platform=platform))
                continue

            try:
                # most of the time we're building nightlies, so check the snap_release key
                # to see if a nightly release string was stashed
                release = package['snap_release']
            except KeyError:
                release = package['release']

            evr = EVR(package['version'], release)

            # dist_release add the dist macro to the spec release
            set_spec_release(specfile, evr.dist_release)
            set_spec_version(specfile, evr.version)

            command = ("mock --no-clean -r {chroot} --buildsrpm --spec {spec} -D 'dist .{platform}'"
                       " --sources {source_dir} --resultdir {destination}")
            command = command.format(chroot=mock_root, spec=specfile, source_dir=source_dir,
                                     platform=platform, destination=destination)
            print('Running "' + command + '"')
            try:
                subprocess.check_output(command, shell=True)
            except subprocess.CalledProcessError as e:
                print('Failed to build SRPM: \n' + str(e.output))


def build_rpms(config_path, srpm_dir, dest=None, platforms=None, package_names=None,
               use_copr=False):
    """Build RPMs in either mock roots or Copr."""
    config = load_config(config_path)
    combined = list(config['pulp-packages'].items()) + list(config['external-deps'].items())
    if package_names:
        packages = {}
        for name, package in combined:
            if name in package_names:
                packages[name] = package
    else:
        packages = dict(combined)

    platforms = config['platforms'] if platforms is None else platforms

    if use_copr:
        # XXX copr builds aren't smart enough yet to deal with the build-deps list.
        #     for that to work, and since each build dep potentially requires the
        #     one before it to proceed, we should probably build them in-order, blocking
        #     until all tasks succeed, before pushing all the SRPMs up in bulk. We should
        #     also do this in its own loop, so we don't have to wait all over again when
        #     submitting for different platforms or copr projects

        # get a copr client, check to see what EVRs it knows about for this package,
        # only submit what's needed
        coprs = config['copr-projects']
        copr_client = copr.create_client2_from_file_config()

        # this is a mapping of copr_project: {dist: {package_name: package_version}}, used
        # to decide which package to actually build, since copr will gladly build
        # packages with the same nevra. Do this before the platform loop so we don't
        # ask copr for the same thing on every platform.

        # stack up defaultdicts so we can easily create the seen package dict, e.g
        # copr_seen_packages[copr_project][dist][package_name]
        copr_seen_packages = defaultdict(lambda: defaultdict(lambda: defaultdict(EVR.lowest)))

        for copr_project in coprs:
            # filter by the project we want, so only one is returned
            try:
                project = copr_client.projects.get_list(search_query=copr_project).projects[0]
            except IndexError:
                print('copr {} not found'.format(copr_project))
                continue
            builds = project.get_builds().builds
            for build in builds:
                if build.state != 'succeeded':
                    continue
                # copr builds have the dist component at the end of the version,
                # include that in the package map
                evr_str, dist = build.package_version.rsplit('.', 1)
                # run the evr string through EVR to normalize it
                evr = EVR.fromstring(evr_str)
                # keep track of the most recent package ver so we can reject lower versions later
                if copr_seen_packages[copr_project][dist][build.package_name] < evr:
                    copr_seen_packages[copr_project][dist][build.package_name] = evr

            for platform in platforms:
                print('Building RPMs for platform {} in copr {}'.format(platform, copr_project))
                platform_srpm_dir = os.path.join(srpm_dir, platform)
                chroots = sorted(config['platforms'][platform])
                for name, package in packages.items():
                    try:
                        release = package['snap_release']
                    except KeyError:
                        release = package['release']

                    build_evr = EVR(package['version'], release)
                    # duplicate evr check
                    seen_evr = copr_seen_packages[copr_project][platform][name]
                    if seen_evr >= build_evr:
                        prefix = '-'.join((name, str(build_evr)))
                        srpm = '.'.join((prefix, platform, 'src', 'rpm'))
                        srpm_abspath = os.path.join(platform_srpm_dir, srpm)
                        try:
                            project.create_build_from_file(srpm_abspath, chroots=chroots)
                            print('{} submitted to copr {} for {}'.format(
                                  os.path.basename(srpm), copr_project, ', '.join(chroots)))
                        except IOError:
                            # no srpm for this package build
                            print('SRPM not found: {}'.format(srpm_abspath))
    else:
        for platform in platforms:
            print('Building RPMs for platform {}'.format(platform))
            platform_srpm_dir = os.path.join(srpm_dir, platform)
            platform_rpm_dir = os.path.join(dest, platform)
            os.makedirs(platform_rpm_dir, exist_ok=True)
            chroots = sorted(config['platforms'][platform])
            for name, package in packages.items():
                mock_rpm(chroots, platform_srpm_dir, platform_rpm_dir, name, package, config)


def mock_rpm(chroots, srpm_dir, rpm_dir, name, package, config):
    """Build an RPM with Mock, installing RPMs specified in the config"""
    install_command = "mock -r {chroot} -i {rpms}"
    build_command = ("mock --no-clean -r {chroot} --resultdir {destination} {srpm}")

    srpms = [f for f in os.listdir(srpm_dir) if f.endswith('src.rpm')]
    package_prefix = name + '-' + package['version']
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
        print('Skipping {pkg} since no SRPM is present'.format(pkg=name))


def find_files_matching_pattern(root_directory, pattern):
    """
    Find all spec files within a given root directory

    :param root_directory: The directory to search
    :type root_directory: str
    :param pattern: The regex to match files in a directory
    :type pattern: str`
    :return: list of canonical paths to spec files
    :rtype: list of str
    """
    # XXX This could probably be done by builting glob functionality, but
    #     these special dirs get in the way. Better solution is to reduce
    #     this list to only tests, then don't put versions in tests.
    ignored_dirs = ('playpen', 'test', 'deps', 'build')
    for root, dirnames, filenames in os.walk(root_directory):
        # don't look for things in playpen or testing directories
        if any(root.startswith(dirname) for dirname in ignored_dirs):
            continue

        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)


def replace_version_in_files(root_directory, file_mask, new_version, version_regex):
    version_regex = re.compile(version_regex, re.IGNORECASE)

    for py_file in find_files_matching_pattern(root_directory, file_mask):
        version_updated = False
        with open(py_file, 'r') as py_fp:
            py_lines = py_fp.readlines()

        with open(py_file, 'w') as py_fp:
            for line in py_lines:
                match = version_regex.match(line)
                if match:
                    # As seen by inspecting _PY_RE_BASE, the match group we're trying to replace
                    # is the seventh, the version string itself, while keeping everything else the
                    # same. Group 0 (the entire match string) is excluded, so index 6 is what needs
                    # to change.
                    result = list(match.groups())
                    result[6] = new_version
                    line = ''.join(result) + '\n'
                    version_updated = True
                py_fp.write(line)
        if version_updated:
            print('{} updated to version {}'.format(py_file, new_version))
