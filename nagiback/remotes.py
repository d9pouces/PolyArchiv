# -*- coding=utf-8 -*-
from __future__ import unicode_literals

from nagiback.utils import Repository
from nagiback.locals import GitRepository as LocalGitRepository

__author__ = 'mgallet'


class RemoteRepository(Repository):
    def __init__(self, remote_tags=None, included_local_tags=None, excluded_local_tags=None):
        self.remote_tags = self._split_tags(remote_tags)
        self.included_local_tags = self._split_tags(included_local_tags)
        self.excluded_local_tags = self._split_tags(excluded_local_tags)

    def backup(self, local_repository):
        raise NotImplementedError


class GitRepository(RemoteRepository):
    def __init__(self, remote_tags=None, included_local_tags=None, excluded_local_tags=None):
        super(GitRepository, self).__init__(remote_tags=remote_tags, included_local_tags=included_local_tags,
                                            excluded_local_tags=excluded_local_tags)

    def backup(self, local_repository):
        assert local_repository.__class__ == LocalGitRepository
        raise NotImplementedError
#
#
# class RsyncRepository(RemoteRepository):
#     def __init__(self, remote_tags=None, included_local_tags=None, excluded_local_tags=None):
#         super(GitRepository, self).__init__(remote_tags=remote_tags, included_local_tags=included_local_tags,
#                                             excluded_local_tags=excluded_local_tags)
