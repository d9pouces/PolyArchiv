# -*- coding=utf-8 -*-
from __future__ import unicode_literals

from nagiback.utils import Repository

__author__ = 'mgallet'


class RemoteRepository(Repository):
    def __init__(self, remote_tags=None, included_local_tags=None, excluded_local_tags=None):
        self.remote_tags = self._split_tags(remote_tags)
        self.included_local_tags = self._split_tags(included_local_tags)
        self.excluded_local_tags = self._split_tags(excluded_local_tags)

    def run(self, local_repository):
        raise NotImplementedError


class GitRepository(Repository):
    def __init__(self, remote_tags=None, included_local_tags=None, excluded_local_tags=None):
        self.remote_tags = self._split_tags(remote_tags)
        self.included_local_tags = self._split_tags(included_local_tags)
        self.excluded_local_tags = self._split_tags(excluded_local_tags)

    def run(self, local_repository):
        raise NotImplementedError
