#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
from polyarchiv.cli import main
__author__ = 'mgallet'
engines_file = os.path.abspath(os.path.join(__file__, '..', 'engines.ini'))
if not os.path.isfile(engines_file):
    engines_file = None
sys.exit(main(engines_file=engines_file))
