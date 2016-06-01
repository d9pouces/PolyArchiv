#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import polyarchiv
from polyarchiv.cli import main
__author__ = 'Matthieu Gallet'

engines_file = os.path.abspath(os.path.join(polyarchiv.__file__, os.path.pardir, os.path.pardir, 'engines.ini'))
if not os.path.isfile(engines_file):
    engines_file = None
sys.exit(main(engines_file=engines_file))
