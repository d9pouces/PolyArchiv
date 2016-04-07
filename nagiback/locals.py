# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
import subprocess

from nagiback.conf import Parameter, strip_split, check_directory, check_executable
from nagiback.repository import Repository

__author__ = 'mgallet'


class LocalRepository(Repository):
    """Local repository, made of one or more sources.
     Each source is run and contribute to new
    """
    parameters = Repository.parameters + [
        Parameter('log_size', converter=int),
        Parameter('local_tags', converter=strip_split),
        Parameter('included_remote_tags', converter=strip_split),
        Parameter('excluded_remote_tags', converter=strip_split),
    ]

    def __init__(self, name, log_size=None, local_tags=None, included_remote_tags=None, excluded_remote_tags=None,
                 **kwargs):
        super(LocalRepository, self).__init__(name=name, **kwargs)
        self.log_size = log_size
        self.local_tags = local_tags or []
        self.included_remote_tags = included_remote_tags or []
        self.excluded_remote_tags = excluded_remote_tags or []
        self.sources = []

    def backup(self):
        """ perform the backup and log all errors
        """
        self.get_lock()
        self.do_backup()
        self.release_lock()

    def add_source(self, source):
        """
        :param source: source
        :type source: :class:`nagiback.sources.Source`
        """
        self.sources.append(source)

    def get_cwd(self):
        """Must return a valid directory where a source can write its files.
        If the local repository is not the filesystem, any file written in this directory by a source must be stored
        to the local repository's storage.
        """
        raise NotImplementedError

    def do_backup(self):
        raise NotImplementedError

    def get_log(self):
        raise NotImplementedError

    def add_log(self):
        raise NotImplementedError

    def get_lock(self):
        raise NotImplementedError

    def release_lock(self):
        raise NotImplementedError


class FileRepository(LocalRepository):
    parameters = LocalRepository.parameters + [
        Parameter('local_path', converter=check_directory)
    ]

    def __init__(self, name, local_path='.', **kwargs):
        super(FileRepository, self).__init__(name=name, **kwargs)
        self.local_path = local_path

    def do_backup(self):
        if not os.path.isdir(self._private_path) and os.path.exists(self._private_path):
            raise ValueError('%s exists and is not a directory' % self._private_path)
        elif not os.path.isdir(self._private_path):
            os.makedirs(self._private_path)
        for source in self.sources:
            source.backup()

    def get_cwd(self):
        return self.local_path

    @property
    def _private_path(self):
        return os.path.join(self.local_path, '.nagiback')

    @property
    def _lock_filepath(self):
        return os.path.join(self._private_path, 'lock')


class GitRepository(FileRepository):
    parameters = FileRepository.parameters + [
        Parameter('git_executable', converter=check_executable),
    ]

    def __init__(self, name, git_executable='git', **kwargs):
        super(GitRepository, self).__init__(name=name, **kwargs)
        self.git_executable = git_executable

    def do_backup(self):
        super(GitRepository, self).backup()
        end = datetime.datetime.now()
        subprocess.Popen([self.git_executable, 'init'], cwd=self.local_path)
        subprocess.Popen([self.git_executable, 'commit', 'add', '.'], cwd=self.local_path)
        subprocess.Popen([self.git_executable, 'commit', '-am', end.strftime('Backup %Y/%m/%d %H:%M')],
                         cwd=self.local_path)
