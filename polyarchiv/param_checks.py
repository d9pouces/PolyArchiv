# coding=utf-8
from __future__ import unicode_literals


def gitlab_projectname(value):
    left, sep, right = value.partition('/')
    if sep != '/':
        raise ValueError('project name must be of the form \'namespace/project\'')
    if '/' in left or '/' in right:
        raise ValueError('project name must be of the form \'namespace/project\'')


def check_archive(value):
    if value.endswith('.tar.gz'):
        return value
    elif value.endswith('.tar.bz2'):
        return value
    elif value.endswith('.tar.xz'):
        return value
    raise ValueError('Archive name must end by .tar.gz, .tar.bz2 or .tar.xz')
