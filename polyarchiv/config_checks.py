# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import

__author__ = 'Matthieu Gallet'


class AttributeUniquess(object):
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __call__(self, runner, point, collect_points):
        pass


class FileIsReadable(object):
    def __init__(self, attr_name, required=False):
        self.attr_name = attr_name
        self.required = required

    def __call__(self, runner, point, collect_points):
        pass


class CaCertificate(FileIsReadable):

    def __call__(self, runner, point, collect_points):
        pass


class Email(object):
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __call__(self, runner, point, collect_points):
        pass


class GitUrl(AttributeUniquess):

    def __call__(self, runner, point, collect_points):
        pass
