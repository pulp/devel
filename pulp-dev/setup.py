import sys

from setuptools import setup, find_packages

install_requires = ['pyyaml', 'copr']

setup(
    name='pulp-dev',
    version='1.0.dev1',
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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    entry_points={
        'console_scripts': [
            'pulp-dev = pulp_dev.commands.pulp_dev:main',
        ]
    },
)
