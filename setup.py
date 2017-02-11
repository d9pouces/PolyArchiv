# -*- coding: utf-8 -*-
"""Setup file for the Polyarchiv project.
"""

import codecs
import os.path
import re
import sys
from setuptools import setup, find_packages

try:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from configparser import RawConfigParser, Error as ConfigError
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from ConfigParser import RawConfigParser, Error as ConfigError

version = None
for line in codecs.open(os.path.join('polyarchiv', '__init__.py'), 'r', encoding='utf-8'):
    matcher = re.match(r"""^__version__\s*=\s*['"](.*)['"]\s*$""", line)
    version = version or matcher and matcher.group(1)


with codecs.open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as fd:
    long_description = fd.read()

sources, backup_points, collect_points, filters, hooks = [], [], [], [], []
engines_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engines.ini')

if os.path.isfile(engines_file):
    parser = RawConfigParser()
    parser.read([engines_file])
    if parser.has_section('sources'):
        sources = ['%s = %s' % (key, value) for key, value in parser.items('sources')]
    if parser.has_section('backup_points'):
        backup_points = ['%s = %s' % (key, value) for key, value in parser.items('backup_points')]
    if parser.has_section('collect_points'):
        collect_points = ['%s = %s' % (key, value) for key, value in parser.items('collect_points')]
    if parser.has_section('filters'):
        filters = ['%s = %s' % (key, value) for key, value in parser.items('filters')]
    if parser.has_section('hooks'):
        hooks = ['%s = %s' % (key, value) for key, value in parser.items('hooks')]
command_suffix = '3' if sys.version_info[0] == 3 else ''

setup(
    name='polyarchiv',
    version=version,
    description='Multiple-source backup tool: backup files|MySQL|LDAP|PostgresSQL to git|rsync|tar archives',
    long_description=long_description,
    author='Matthieu Gallet',
    author_email='mgallet@19pouces.net',
    license='CeCILL-B',
    url='https://github.com/d9pouces/Polyarchiv',
    entry_points={'console_scripts': ['polyarchiv%s = polyarchiv.cli:main' % command_suffix],
                  'polyarchiv.sources': sources, 'polyarchiv.backup_points': backup_points,
                  'polyarchiv.collect_points': collect_points, 'polyarchiv.filters': filters,
                  'polyarchiv.hooks': hooks, },
    packages=[x for x in find_packages() if 'tests' not in x],
    include_package_data=True,
    zip_safe=False,
    install_requires=['setuptools>=1.0', ],
    setup_requires=[],
    classifiers=['Development Status :: 4 - Beta', 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: POSIX :: BSD', 'Operating System :: POSIX :: Linux', 'Operating System :: Unix',
                 'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)',
                 'Programming Language :: Python :: 2.7', 'Programming Language :: Python :: 3.3',
                 'Programming Language :: Python :: 3.4', 'Programming Language :: Python :: 3.5', ],
)
