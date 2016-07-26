"""
This module contains console command entry points for release engineering tools.
"""
import os

from ... import releng_utils


def add_subcommands(subparsers):
    """
    Adds sub-commands provided for release engineering.
    """
    # archive subcommand
    archive_parser = subparsers.add_parser(
        'archive', description='Fetch archives for Pulp and its dependencies'
    )
    archive_parser.add_argument('config', help='YAML file describing the versions of each project')
    archive_parser.add_argument(
        '--spec-dir',
        help='Path to the Pulp packaging repository',
        default=os.path.join(os.getcwd(), 'packaging')
    )
    archive_parser.add_argument('--clean', '-c', default=False, action='store_true',
                                help='Remove existing clones before trying to clone.')
    archive_parser.add_argument(
        'package_names',
        help='The names of the packages to fetch; if unspecified all packages are fetched',
        nargs='*'
    )
    archive_parser.set_defaults(func=fetch_archives)

    # srpm subcommand
    srpm_parser = subparsers.add_parser('srpm', description='Build SRPMs')
    srpm_parser.add_argument(
        '--spec-dir',
        help='Path to the Pulp packaging repository',
        default=os.path.join(os.getcwd(), 'packaging')
    )
    srpm_parser.add_argument('--clean', '-c', default=False, action='store_true',
                             help='Remove existing SRPMs before building new ones.')
    srpm_parser.add_argument(
        '--platform',
        help='Platform to build SRPMs for; if unspecified SRPMs are built for all platforms',
        nargs='*'
    )
    srpm_parser.add_argument(
        'config',
        help='YAML file describing the versions of each project',
    )
    srpm_parser.add_argument(
        'package_names',
        help='The names of the packages to build; if unspecified all packages are built',
        nargs='*',
    )
    srpm_parser.set_defaults(func=build_srpms)

    # rpm subcommand
    rpm_parser = subparsers.add_parser(
        'rpm', description='Build the SRPMs for all Pulp projects and deps'
    )
    rpm_parser.add_argument(
        '--srpm-dir',
        help='location of the SRPM directory containing SRPMs for each platform',
        default=os.path.join(os.getcwd(), 'SRPMS'),
    )
    rpm_parser.add_argument(
        '--platform',
        help='Platform to build RPMs for; if unspecified RPMs are built for all platforms',
        nargs='*',
        dest='platforms'
    )
    rpm_parser.add_argument('-c', '--copr', help='build rpms in copr rather than mock roots',
                            action='store_true')
    rpm_parser.add_argument(
        '-d', '--with-deps', default=False, action='store_true',
        help='build dependencies in addition to Pulp packages',
    )
    rpm_parser.add_argument(
        'config',
        help='YAML file describing the versions of each project',
    )
    rpm_parser.add_argument(
        'package_names',
        help='The names of the packages to build; if unspecified all packages are built',
        nargs='*',
    )
    rpm_parser.set_defaults(func=build_rpms)

    # update_version subcommand
    update_version_parser = subparsers.add_parser(
        'update-version', description='Update Specfile Versions')
    update_version_group = update_version_parser.add_mutually_exclusive_group(required=True)
    update_version_parser.add_argument(
        'specfile',
        help='Path to a spec file to update',
    )
    update_version_group.add_argument(
        '--update-type', '-t', default='stage',
        choices=['major', 'minor', 'patch', 'release', 'stage'],
        help='Type of version update to apply'
    )
    update_version_group.add_argument(
        '--evr', '-e', default=None,
        help='Manually specify full EVR ([epoch:]version-release) to write to spec files, '
        'only used if update-type is version.'
    )
    update_version_parser.add_argument(
        '--stage', '-s', default=None, choices=['alpha', 'beta', 'rc'],
        help='Manually specify next release state, useful if skipping a stage.'
    )
    update_version_parser.add_argument(
        '--dry-run', '-d', default=False, action='store_true',
        help="Don't actually update the spec file, just print what would be changed."
    )
    update_version_parser.set_defaults(func=update_version)


def fetch_archives(args):
    """
    Fetch all archives for Pulp and its dependencies.
    """
    config = releng_utils.load_config(args.config)
    releng_utils.pulp_tarballs(config, args.spec_dir, args.clean)
    releng_utils.deps_tarballs(config, args.spec_dir)
    releng_utils.write_config(args.config, config)


def build_srpms(args):
    """
    Build source RPMs.

    This expects that the source tarballs and any patches are present in a
    directory in packages/rpms/<package-name>/sources/.
    """
    config = releng_utils.load_config(args.config)
    releng_utils.build_srpms(config, args.spec_dir, args.package_names, clean=args.clean)


def build_rpms(args):
    """Build RPMs from SRPMs."""
    # TODO make arg
    rpm_dir = os.path.join(os.getcwd(), 'RPMS')
    releng_utils.build_rpms(args.config, args.srpm_dir, rpm_dir, args.platforms,
                            args.package_names, args.copr)


def update_version(args):
    if args.evr:
        # user specified version
        evr = releng_utils.EVR.fromstring(args.evr)
    else:
        update = {
            args.update_type: True
        }
        if args.stage:
            update['next_stage'] = args.stage
        evr = releng_utils.get_spec_evr(args.specfile)
        evr = evr.increment(**update)

    if args.dry_run:
        print('Would write EVR {} to {}'.format(evr, args.specfile))
    else:
        releng_utils.set_spec_evr(args.specfile, evr)
        print('Wrote EVR {} to {}'.format(evr, args.specfile))
