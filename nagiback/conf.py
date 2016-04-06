# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import os

from nagiback.utils import text_type

__author__ = 'mgallet'


def bool_setting(value):
    return text_type(value).lower() in {'1', 'ok', 'yes', 'true', 'on'}


def str_or_none(text):
    return text or None


def str_or_blank(value):
    return '' if value is None else text_type(value)


def strip_split(value):
    """Split the value on "," and strip spaces of the result. Remove empty values.

    >>> strip_split('keyword1, keyword2 ,,keyword3')
    ["keyword1", "keyword2", "keyword3"]

    >>> strip_split('')
    []

    >>> strip_split(None)
    []

    :param value:
    :type value:
    :return:
    :rtype:
    """
    if value:
        return [x.strip() for x in value.split(',') if x.strip()]
    return []


def check_directory(value):
    """Check if value is a valid directory path. If not, raise a ValueError, else return the value
    """
    if os.path.isdir(value):
        return value
    raise ValueError('%s is not a valid directory' % value)


def check_executable(value):
    """TODO check if value is a valid executable"""
    return True


class Parameter(object):
    """class that maps an option in a .ini file to a argument name."""

    def __init__(self, arg_name, option_name=None, converter=str, to_str=str_or_blank, help_str=None):
        """:param arg_name: the name of parameter passed to the engine
        :type arg_name: `str`
        :param option_name: option name in a .ini file
        :type option_name: `str`
        :param converter: any callable that takes a text value and returns an object. Default to `str_or_none`
        :type converter: `callable`
        :param to_str: any callable that takes the Python value and that converts it to str
            only used for writing sample config file. Default to `str`
        :type to_str: `callable`
        :param help_str: any text that can serve has help in documentation.
            If None, then `settings.%s_HELP % setting_name` will be used as help text.
        :type help_str: `str`
        """
        self.arg_name = arg_name
        self.option_name = option_name or arg_name
        self.converter = converter
        self.to_str = to_str
        self.help_str = help_str

    def __str__(self):
        return self.option