# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import subprocess

from nagiback.utils import Repository
from nagiback.locals import GitRepository as LocalGitRepository

__author__ = 'mgallet'


class RemoteRepository(Repository):
    def __init__(self, name, remote_tags=None, included_local_tags=None, excluded_local_tags=None):
        super(RemoteRepository, self).__init__(name)
        self.remote_tags = self._split_tags(remote_tags)
        self.included_local_tags = self._split_tags(included_local_tags)
        self.excluded_local_tags = self._split_tags(excluded_local_tags)

    def backup(self, local_repository):
        self.do_backup(local_repository)

    def do_backup(self, local_repository):
        raise NotImplementedError


class GitRepository(RemoteRepository):
    def __init__(self, name, remote_url='', git_executable='git',
                 remote_tags=None, included_local_tags=None, excluded_local_tags=None):
        super(GitRepository, self).__init__(name, remote_tags=remote_tags, included_local_tags=included_local_tags,
                                            excluded_local_tags=excluded_local_tags)
        self.remote_url = remote_url
        self.git_executable = git_executable

    def do_backup(self, local_repository):
        assert local_repository.__class__ == LocalGitRepository
        assert isinstance(local_repository, LocalGitRepository)
        cmd = [self.git_executable, 'remote']
        # noinspection PyUnresolvedReferences
        output = subprocess.check_output(cmd, cwd=local_repository.local_path).decode()
        existing_remotes = {x.strip() for x in output.splitlines()}
        if self.name not in existing_remotes:
            cmd = [self.git_executable, 'remote', 'add', '-t', 'master', 'master', self.name, self.remote_url]
            subprocess.check_call(cmd, cwd=local_repository.local_path)
        cmd = [self.git_executable, 'push', self.name]
        subprocess.check_call(cmd, cwd=local_repository.local_path)

#
#
# class RsyncRepository(RemoteRepository):
#     def __init__(self, name, remote_tags=None, included_local_tags=None, excluded_local_tags=None):
#         super(GitRepository, self).__init__(name, remote_tags=remote_tags, included_local_tags=included_local_tags,
#                                             excluded_local_tags=excluded_local_tags)
