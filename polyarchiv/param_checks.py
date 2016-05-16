# coding=utf-8
from __future__ import unicode_literals


def gitlab_projectname(value):
    left, sep, right = value.partition('/')
    if sep != '/':
        raise ValueError('project name must be of the form \'namespace/project\'')
    if '/' in left or '/' in right:
        raise ValueError('project name must be of the form \'namespace/project\'')
