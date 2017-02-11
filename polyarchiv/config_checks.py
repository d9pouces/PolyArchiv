# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import

import os
import re

from polyarchiv.utils import normalize_ssh_url

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse, urlencode, quote_plus
except ImportError:
    # noinspection PyCompatibility, PyUnresolvedReferences
    from urlparse import urlparse
    # noinspection PyUnresolvedReferences
    from urllib import urlencode, quote_plus

__author__ = 'Matthieu Gallet'


class AttributeCheck(object):
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __call__(self, runner, point, associated_points):
        pass


class AttributeUniquess(AttributeCheck):
    def __call__(self, runner, point, collect_points):
        value = getattr(point, self.attr_name)
        if value is None:
            return
        values = {point.format_value(value, collect_point) for collect_point in collect_points}
        if len(values) == 1 and len(collect_points) > 1:
            msg = '%s.%s = %s does not depend on the the collect point. You should append "{name}"' % \
                  (point.name, self.attr_name, values.pop())
            runner.print_error(msg)


class FileIsReadable(object):
    def __init__(self, attr_name, required=False):
        self.attr_name = attr_name
        self.required = required

    # noinspection PyUnusedLocal
    def __call__(self, runner, point, collect_points):
        value = getattr(point, self.attr_name)
        if not value and self.required:
            runner.print_error('%s.%s should be defined' % (point.name, self.attr_name))
        if not value:
            return
        for collect_point in collect_points:
            formatted_value = point.format_value(value, collect_point)
            self.read_file(point, collect_point, formatted_value)

    def read_file(self, point, collect_point, formatted_value):
        if not os.path.isfile(formatted_value):
            collect_point.print_error('%s.%s does not exist for the collect point %s (%s)'
                                      % (point.name, self.attr_name, collect_point.name, formatted_value))
        else:
            try:
                open(formatted_value, 'rb').read(1)
            except IOError:
                collect_point.print_error('%s.%s can not be read by the collect point %s (%s)'
                                          % (point.name, self.attr_name, collect_point.name, formatted_value))


class CaCertificate(FileIsReadable):
    def read_file(self, point, collect_point, formatted_value):
        if formatted_value == 'any':
            return
        super(CaCertificate, self).read_file(point, collect_point, formatted_value)


class Email(AttributeCheck):
    # noinspection PyUnusedLocal
    def __call__(self, runner, point, collect_points):
        value = getattr(point, self.attr_name)
        for collect_point in collect_points:
            formatted_value = point.format_value(value, collect_point)
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", formatted_value):
                runner.print_error('%s.%s does not define a valid e-mail address for the collect point %s (%s)'
                                   % (point.name, self.attr_name, collect_point.name, formatted_value))


class ValidGitUrl(AttributeCheck):
    def __call__(self, runner, point, collect_points):
        value = getattr(point, self.attr_name)
        for collect_point in collect_points:
            remote_url = point.format_value(value, collect_point)
            remote_url = normalize_ssh_url(remote_url)
            parsed_url = urlparse(remote_url)
            scheme = parsed_url.scheme
            if scheme and scheme not in ('ssh', 'git', 'http', 'https', 'ftp', 'ftps', 'rsync', 'file',):
                runner.print_error('%s.%s does not define a valid git URL for the collect point %s (%s)'
                                   % (point.name, self.attr_name, collect_point.name, remote_url))


class GitlabProjectName(AttributeCheck):
    def __call__(self, runner, point, collect_points):
        value = getattr(point, self.attr_name)
        for collect_point in collect_points:
            project_name = point.format_value(value, collect_point)
            if not re.match(r'[a-zA-Z_][a-zA-Z_\-\d]*/[a-zA-Z_][a-zA-Z_\-\d]*', project_name):
                runner.print_error('%s.%s does not define a valid Gitlab project name for the collect point %s (%s)'
                                   % (point.name, self.attr_name, collect_point.name, project_name))


class ValidSvnUrl(AttributeCheck):
    def __call__(self, runner, point, backup_points):
        remote_url = getattr(point, self.attr_name)
        parsed_url = urlparse(remote_url)
        scheme = parsed_url.scheme
        if scheme and scheme not in ('svn', 'http', 'https', 'file',):
            runner.print_error('%s.%s does not define a valid svn URL (%s)' % (point.name, self.attr_name, remote_url))
