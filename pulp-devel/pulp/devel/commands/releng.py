"""
This module contains console command entry points for release engineering tools.
"""
import os

from .. import releng_utils


def add_subcommands(subparsers):
    """
    Adds sub-commands provided for release engineering.
    """
    # archive subcommand
    archive_parser = subparsers.add_parser('archive', description='Fetch archives for Pulp and its dependencies')
    archive_parser.add_argument('config', help='YAML file describing the versions of each project')
    archive_parser.add_argument(
        '--spec-dir',
        help='Path to the Pulp packaging repository',
        default=os.path.join(os.getcwd(), 'packaging')
    )
    archive_parser.add_argument(
        'package-names',
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
        'package-names',
        help='The names of the packages to build; if unspecified all packages are built',
        nargs='*',
    )
    srpm_parser.set_defaults(func=build_srpms)

    # rpm subcommand
    rpm_parser = subparsers.add_parser('rpm', description='Build the SRPMs for all Pulp projects and deps')
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
    rpm_parser.add_argument('-d', '--with-deps', help='build dependencies in addition to Pulp packages',
                            action='store_true')
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


def fetch_archives(args):
    """
    Fetch all archives for Pulp and its dependencies.
    """
    config = releng_utils.load_config(args.config)
    releng_utils.pulp_tarballs(config, args.spec_dir)
    releng_utils.deps_tarballs(config, args.spec_dir)
    releng_utils.write_config(args.config, config)


def build_srpms(args):
    """
    Build source RPMs.

    This expects that the source tarballs and any patches are present in a
    directory in packages/rpms/<package-name>/sources/.
    """
    config = releng_utils.load_config(args.config)
    releng_utils.build_srpms(config, args.spec_dir)


def build_rpms(args):
    """Build RPMs from SRPMs."""
    # TODO make arg
    rpm_dir = os.path.join(os.getcwd(), 'RPMS')
    releng_utils.build_rpms(args.config, args.srpm_dir, rpm_dir, args.platforms,
                            args.package_names, args.copr)
