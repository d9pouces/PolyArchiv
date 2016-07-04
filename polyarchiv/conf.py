# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import os

import pwd

from polyarchiv.utils import text_type

__author__ = 'Matthieu Gallet'


def bool_setting(value):
    return text_type(value).lower() in {'1', 'ok', 'yes', 'true', 'on'}


def check_username(value):
    if value not in {x[0] for x in pwd.getpwall()}:
        raise ValueError('%s is not a valid user' % value)
    return value


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


def check_file(value):
    """Check if value is a valid directory path. If not, raise a ValueError, else return the value
    """
    if os.path.isfile(value):
        return value
    raise ValueError('%s is not a valid file' % value)


def check_executable(value):
    """TODO check if value is a valid executable"""
    if os.path.isfile(value):
        return True
    path = os.environ.get('PATH', '')
    for search_dir in path.split(':'):
        if os.path.isfile(os.path.join(search_dir, value)):
            return True
    raise ValueError('Executable \'%s\' not found in $PATH=%s' % (value, path))


class CheckOption(object):
    def __init__(self, valid_options):
        """Check if the provided value is among the allowed ones"""
        self.valid_options = valid_options  # list of valid options

    def __call__(self, value):
        if value in self.valid_options:
            return value
        raise ValueError('%s is not valid. Please select one of %s' % (value, ', '.join(self.valid_options)))


class Parameter(object):
    """class that maps an option in a .ini file to a argument name."""

    def __init__(self, arg_name, option_name=None, converter=str, to_str=str_or_blank, help_str=None, required=False,
                 common=False, default_str_value=None):
        """:param arg_name: the name of parameter passed to the engine
        :type arg_name: `str` or `unicode`
        :param option_name: option name in a .ini file
        :type option_name: `str` or `unicode`
        :param converter: any callable that takes a text value and returns an object. Default to `str_or_none`
        :type converter: `callable`
        :param to_str: any callable that takes the Python value and that converts it to str
            only used for writing sample config file. Default to `str`
        :type to_str: `callable`
        :param help_str: any text that can serve has help in documentation.
            If None, then `settings.%s_HELP % setting_name` will be used as help text.
        :type help_str: `str` or `unicode`
        :param required: this parameter is required
        :param common: this parameter is globally defined and has the same value for all ParameterizedObjects
        :param default_str_value: default value (string value)
        """
        self.arg_name = arg_name
        self.option_name = option_name or arg_name
        self.converter = converter
        self.to_str = to_str
        self.help_str = help_str
        self.required = required
        self.common = common
        self.default_str_value = default_str_value

    def __str__(self):
        return self.option_name
