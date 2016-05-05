# -*- coding: utf-8 -*-
"""Setup file for the Polysauv project.
"""

import codecs
import os.path
import re
from setuptools import setup

version = None
for line in codecs.open(os.path.join('polysauv', '__init__.py'), 'r', encoding='utf-8'):
    matcher = re.match(r"""^__version__\s*=\s*['"](.*)['"]\s*$""", line)
    version = version or matcher and matcher.group(1)

with codecs.open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as fd:
    long_description = fd.read()

sources = ['RSync = polysauv.sources:RSync',
           'MySQL = polysauv.sources:MySQL',
           'PostgresSQL = polysauv.sources:PostgresSQL',
           'Ldap = polysauv.sources:Ldap', ]
remotes = ['GitRepository = polysauv.remotes:GitRepository',
           'Rsync = polysauv.remotes:Rsync',
           'TarArchive = polysauv.remotes:TarArchive',
           'Duplicity = polysauv.remotes:Duplicity', ]
locals_ = ['FileRepository = polysauv.locals:FileRepository',
           'GitRepository = polysauv.locals:GitRepository', ]

setup(
    name='polysauv',
    version=version,
    description='Multiple-source backup tool: backup files|MySQL|LDAP|PostgresSQL to git|rsync|duplicity|tar archives',
    long_description=long_description,
    author='mgallet',
    author_email='mgallet@19pouces.net',
    license='CeCILL-B',
    url='https://github.com/d9pouces/Polysauv',
    entry_points={'console_scripts': ['polysauv = polysauv.cli:main'],
                  'polysauv.sources': sources, 'polysauv.remotes': remotes, 'polysauv.locals': locals_, },
    packages=['polysauv', ],
    include_package_data=True,
    zip_safe=False,
    install_requires=['setuptools>=1.0', ],
    setup_requires=[],
    classifiers=['Development Status :: 4 - Beta', 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: POSIX :: BSD', 'Operating System :: POSIX :: Linux', 'Operating System :: Unix',
                 'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)',
                 'Programming Language :: Python :: 2.7', 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5', 'Programming Language :: Python :: 3.6'],
)
