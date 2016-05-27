# coding: utf-8
# Copyright (c) 2008-2011 Volvox Development Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Author: Konstantin Lepa <konstantin.lepa@gmail.com>

"""ANSII Color formatting for output in terminal."""

from __future__ import print_function

import codecs
import os

import sys

__ALL__ = ['colored', 'cprint']

VERSION = (1, 1, 0)

BOLD = 'bold'
DARK = 'dark'
UNDERLINE = 'underline'
BLINK = 'blink'
REVERSE = 'reverse'
CONCEALED = 'concealed'
ATTRIBUTES = dict(list(zip([BOLD, DARK, '', UNDERLINE, BLINK, '', REVERSE, CONCEALED], list(range(1, 9)))))
del ATTRIBUTES['']

ON_GREY = 'on_grey'
ON_RED = 'on_red'
ON_GREEN = 'on_green'
ON_YELLOW = 'on_yellow'
ON_BLUE = 'on_blue'
ON_MAGENTA = 'on_magenta'
ON_CYAN = 'on_cyan'
ON_WHITE = 'on_white'
HIGHLIGHTS = dict(list(zip([ON_GREY, ON_RED, ON_GREEN, ON_YELLOW, ON_BLUE, ON_MAGENTA, ON_CYAN, ON_WHITE],
                           list(range(40, 48)))))

GREY = 'grey'
RED = 'red'
GREEN = 'green'
YELLOW = 'yellow'
BLUE = 'blue'
MAGENTA = 'magenta'
CYAN = 'cyan'
WHITE = 'white'
COLORS = dict(list(zip([GREY, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, ], list(range(30, 38)))))

RESET = '\033[0m'


def colored(text, color=None, on_color=None, attrs=None):
    """Colorize text.

    Available text colors:
        red, green, yellow, blue, magenta, cyan, white.

    Available text highlights:
        on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.

    Available attributes:
        bold, dark, underline, blink, reverse, concealed.

    Example:
        colored('Hello, World!', 'red', 'on_grey', ['blue', 'blink'])
        colored('Hello, World!', 'green')
    """
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        fmt_str = '\033[%dm%s'
        if color is not None:
            text = fmt_str % (COLORS[color], text)

        if on_color is not None:
            text = fmt_str % (HIGHLIGHTS[on_color], text)

        if attrs is not None:
            for attr in attrs:
                text = fmt_str % (ATTRIBUTES[attr], text)

        text += RESET
    return text


def cprint(text, *args, **kwargs):
    """Print colorize text.

    It accepts keyword arguments of print function.
    """
    if sys.version_info[0] == 2 and isinstance(text, str):
        text = text.decode('utf-8')
    attrs = [x for x in args if x in ATTRIBUTES]
    colors = [x for x in args if x in COLORS]
    color = colors[0] if colors else None
    on_colors = [x for x in args if x in HIGHLIGHTS]
    on_color = on_colors[0] if on_colors else None
    if sys.stdout.isatty():
        text = colored(text, color, on_color, attrs)
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
        content = text
    else:
        encoding = os.environ.get('LC_CTYPE', os.environ.get('LC_ALL', '')).partition('.')[2]
        try:
            codecs.lookup(encoding)
        except LookupError:
            encoding = 'utf-8'
        content = text.encode(encoding)
    print(content, **kwargs)
