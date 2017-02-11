# coding=utf-8
from __future__ import unicode_literals, print_function

import os
import sys

sys.path += [os.path.dirname(os.path.dirname(__file__))]

from polyarchiv.termcolor import cprint, RED


if __name__ == '__main__':
    print('*** python%s ***' % sys.version_info[0])
    print('LC_ALL=%s, LC_CTYPE=%s' % (os.environ.get('LC_ALL', ''), os.environ.get('LC_CTYPE', '')))
    print('sys.stdout.encoding=%s, sys.stdout.isatty()=%s' % (sys.stdout.encoding, sys.stdout.isatty()))
    cprint('accents:éè', RED)
    print(' ')
