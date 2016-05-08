# -*- coding: utf-8 -*-
"""Setup file for the Polyarchiv project.
"""

import codecs
import os.path
import re
from setuptools import setup

version = None
for line in codecs.open(os.path.join('polyarchiv', '__init__.py'), 'r', encoding='utf-8'):
    matcher = re.match(r"""^__version__\s*=\s*['"](.*)['"]\s*$""", line)
    version = version or matcher and matcher.group(1)

with codecs.open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as fd:
    long_description = fd.read()

sources = ['rsync = polyarchiv.sources:RSync',
           'mysql = polyarchiv.sources:MySQL',
           'postgressql = polyarchiv.sources:PostgresSQL',
           'ldap = polyarchiv.sources:Ldap', ]
remotes = ['git = polyarchiv.remotes:GitRepository',
           'rsync = polyarchiv.remotes:Rsync',
           'tar = polyarchiv.remotes:TarArchive',
           'duplicity = polyarchiv.remotes:Duplicity', ]
locals_ = ['files = polyarchiv.locals:FileRepository',
           'git = polyarchiv.locals:GitRepository', ]

setup(
    name='polyarchiv',
    version=version,
    description='Multiple-source backup tool: backup files|MySQL|LDAP|PostgresSQL to git|rsync|duplicity|tar archives',
    long_description=long_description,
    author='mgallet',
    author_email='mgallet@19pouces.net',
    license='CeCILL-B',
    url='https://github.com/d9pouces/Polyarchiv',
    entry_points={'console_scripts': ['polyarchiv = polyarchiv.cli:main'],
                  'polyarchiv.sources': sources, 'polyarchiv.remotes': remotes, 'polyarchiv.locals': locals_, },
    packages=['polyarchiv', ],
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
