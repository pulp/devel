import sys

from setuptools import setup, find_packages

PYTHON_MAJOR_MINOR = '%s.%s' % (sys.version_info[0], sys.version_info[1])

install_requires = ['pyyaml']
if PYTHON_MAJOR_MINOR < '2.7':
    install_requires.append('argparse')

setup(
    name='pulp-devel',
    version='1.0.dev0',
    license='GPLv2+',
    packages=find_packages(exclude=['tests']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        ('License :: OSI Approved :: GNU General Public License v2 or later '
         '(GPLv2+)'),
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    entry_points={
        'console_scripts': [
            'pulp-devel = pulp.devel.commands.pulp_devel:main',
        ]
    },
)
