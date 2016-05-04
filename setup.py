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

setup(
    name='polysauv',
    version=version,
    description='Multi-source backup tool',
    long_description=long_description,
    author='mgallet',
    author_email='mgallet@19pouces.net',
    license='CeCILL-B',
    url='https://github.com/d9pouces/Polysauv',
    entry_points={'console_scripts': ['polysauv = polysauv.cli:main']},
    packages=['polysauv', ],
    include_package_data=True,
    zip_safe=False,
    install_requires=['setuptools>=1.0', ],
    setup_requires=[],
    classifiers=['Development Status :: 3 - Alpha', 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: Microsoft :: Windows', 'Operating System :: POSIX :: BSD',
                 'Operating System :: POSIX :: Linux', 'Operating System :: Unix',
                 'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)',
                 'Programming Language :: Python :: 2.7', 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5'],
)
