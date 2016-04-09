# -*- coding=utf-8 -*-
from __future__ import unicode_literals
import logging

import subprocess

import datetime

from nagiback.conf import Parameter, strip_split, check_executable
from nagiback.locals import GitRepository as LocalGitRepository, LocalRepository
from nagiback.repository import Repository, RepositoryInfo
from nagiback.utils import text_type

__author__ = 'mgallet'
logger = logging.getLogger('nagiback.remotes')


class RemoteRepository(Repository):
    parameters = Repository.parameters + [
        Parameter('log_size', converter=int),
        Parameter('remote_tags', converter=strip_split),
        Parameter('included_local_tags', converter=strip_split),
        Parameter('excluded_local_tags', converter=strip_split),
    ]

    def __init__(self, name, remote_tags=None, included_local_tags=None, excluded_local_tags=None, **kwargs):
        super(RemoteRepository, self).__init__(name, **kwargs)
        self.remote_tags = ['remote'] if remote_tags is None else remote_tags
        self.included_local_tags = included_local_tags or []
        self.excluded_local_tags = excluded_local_tags or []

    def backup(self, local_repository):
        """ perform the backup and log all errors
        """
        info = self.get_info(local_repository)
        assert isinstance(info, RepositoryInfo)
        if not self.check_out_of_date_backup(current_time=datetime.datetime.now(), previous_time=info.last_success):
            # the last previous backup is still valid
            # => nothing to do
            return True
        try:
            lock_ = local_repository.get_lock()
            self.do_backup(local_repository)
            local_repository.release_lock(lock_)
            info.success_count += 1
            info.last_state_valid = True
            info.last_success = datetime.datetime.now()
            info.last_message = 'ok'
        except Exception as e:
            info.fail_count += 1
            info.last_fail = datetime.datetime.now()
            info.last_state_valid = False
            info.last_message = text_type(e)
        self.set_info(local_repository, info)
        return info.last_state_valid

    def do_backup(self, local_repository):
        raise NotImplementedError

    def restore(self, local_repository):
        raise NotImplementedError

    # noinspection PyMethodMayBeStatic
    def get_info(self, local_repository, name=None, kind='remote'):
        assert isinstance(local_repository, LocalRepository)
        if name is None:
            name = self.name
        return local_repository.get_info(name, kind=kind)

    # noinspection PyMethodMayBeStatic
    def set_info(self, local_repository, info, name=None, kind='remote'):
        assert isinstance(local_repository, LocalRepository)
        if name is None:
            name = self.name
        return local_repository.set_info(info, name=name, kind=kind)


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
        output = subprocess.check_output(cmd, cwd=local_repository.local_path).decode('utf-8')
        existing_remotes = {x.strip() for x in output.splitlines()}
        if self.name not in existing_remotes:
            cmd = [self.git_executable, 'remote', 'add', '-t', 'master', 'master', self.remote_branch, self.remote_url]
            subprocess.check_call(cmd, cwd=local_repository.local_path)
        cmd = [self.git_executable, 'push', self.remote_branch]
        subprocess.check_call(cmd, cwd=local_repository.local_path)
