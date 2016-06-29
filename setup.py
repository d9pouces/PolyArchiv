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

print(version)

with codecs.open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as fd:
    long_description = fd.read()

sources, remotes, locals_, filters = [], [], [], []
engines_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engines.ini')
print(engines_file)
if os.path.isfile(engines_file):
    parser = RawConfigParser()
    parser.read([engines_file])
    if parser.has_section('sources'):
        sources = ['%s = %s' % (key, value) for key, value in parser.items('sources')]
    if parser.has_section('remotes'):
        remotes = ['%s = %s' % (key, value) for key, value in parser.items('remotes')]
    if parser.has_section('locals'):
        locals_ = ['%s = %s' % (key, value) for key, value in parser.items('locals')]
    if parser.has_section('filters'):
        filters = ['%s = %s' % (key, value) for key, value in parser.items('filters')]
command_suffix = '3' if sys.version_info[0] == 3 else ''

setup(
    name='polyarchiv',
    version=version,
    description='Multiple-source backup tool: backup files|MySQL|LDAP|PostgresSQL to git|rsync|duplicity|tar archives',
    long_description=long_description,
    author='Matthieu Gallet',
    author_email='mgallet@19pouces.net',
    license='CeCILL-B',
    url='https://github.com/d9pouces/Polyarchiv',
    entry_points={'console_scripts': ['polyarchiv%s = polyarchiv.cli:main' % command_suffix],
                  'polyarchiv.sources': sources, 'polyarchiv.remotes': remotes, 'polyarchiv.locals': locals_,
                  'polyarchiv.filters': filters, },
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
