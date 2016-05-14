# coding=utf-8
import sys
import os
sys.path += [os.path.dirname(os.path.dirname(__file__))]

from polyarchiv.termcolor import cprint, RED

print('*** python%s ***' % sys.version_info[0])
print('LC_ALL=%s' % os.environ.get('LC_ALL', ''))
print('LC_CTYPE=%s' % os.environ.get('LC_CTYPE', ''))
print('sys.stdout.encoding=%s' % sys.stdout.encoding)
print('sys.stdout.isatty()=%s' % sys.stdout.isatty())
cprint('accents:éè', RED)
