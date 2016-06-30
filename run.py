#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import polyarchiv
from polyarchiv.cli import main
__author__ = 'Matthieu Gallet'

engines_file = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(polyarchiv.__file__)), 'engines.ini'))
# works even if run.py is symlinked since we use the Python package as reference
if not os.path.isfile(engines_file):
    engines_file = None
sys.exit(main(engines_file=engines_file))
