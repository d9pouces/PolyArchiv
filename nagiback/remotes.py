# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import subprocess

from nagiback.conf import Parameter, strip_split, check_executable
from nagiback.locals import GitRepository as LocalGitRepository, LocalRepository
from nagiback.repository import Repository

__author__ = 'mgallet'


class RemoteRepository(Repository):
    parameters = Repository.parameters + [
        Parameter('log_size', converter=int),
        Parameter('remote_tags', converter=strip_split),
        Parameter('included_local_tags', converter=strip_split),
        Parameter('excluded_local_tags', converter=strip_split),
    ]

    def __init__(self, name, remote_tags=None, included_local_tags=None, excluded_local_tags=None, **kwargs):
        super(RemoteRepository, self).__init__(name, **kwargs)
        self.remote_tags = remote_tags or []
        self.included_local_tags = included_local_tags or []
        self.excluded_local_tags = excluded_local_tags or []

    def backup(self, local_repository):
        self.do_backup(local_repository)

    def do_backup(self, local_repository):
        raise NotImplementedError

    def get_info(self, local_repository, name, kind='remote'):
        assert isinstance(local_repository, LocalRepository)
        return local_repository.get_info(name, kind=kind)

    def set_info(self, local_repository, info, name, kind='remote'):
        assert isinstance(local_repository, LocalRepository)
        return local_repository.set_info(info, name, kind=kind)


class GitRepository(RemoteRepository):
    parameters = RemoteRepository.parameters + [
        Parameter('git_executable', converter=check_executable),
        Parameter('remote_url'),
        Parameter('remote_branch'),
    ]

    def __init__(self, name, remote_url='', remote_branch='master', git_executable='git', **kwargs):
        super(GitRepository, self).__init__(name, **kwargs)
        self.remote_url = remote_url
        self.remote_branch = remote_branch
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
