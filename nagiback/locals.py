# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import os
import subprocess

import datetime

from nagiback.utils import Repository

__author__ = 'mgallet'


class LocalRepository(Repository):
    """Local repository, made of one or more sources.
     Each source is run and contribute to new
    """
    def __init__(self, local_tags='', included_remote_tags='', excluded_remote_tags=''):
        self.local_tags = self._split_tags(local_tags)
        self.included_remote_tags = self._split_tags(included_remote_tags)
        self.excluded_remote_tags = self._split_tags(excluded_remote_tags)
        self.sources = {}

    def add_source(self, name, source):
        """
        :param name: name of the source to add
        :type name: :class:`str`
        :param source: source
        :type source: :class:`nagiback.sources.Source`
        """
        self.sources[name] = source

    def get_cwd(self):
        """Must return a valid directory where a source can write its files.
        If the local repository is not the filesystem, any file written in this directory by a source must be stored
        to the local repository's storage.
        """
        raise NotImplementedError

    def backup(self):
        """ perform the backup and log all errors
        """
        self.do_backup()

    def do_backup(self):
        raise NotImplementedError


class FileRepository(LocalRepository):

    def __init__(self, local_path='.', local_tags='', included_remote_tags='', excluded_remote_tags=''):
        super(FileRepository, self).__init__(local_tags=local_tags, included_remote_tags=included_remote_tags,
                                             excluded_remote_tags=excluded_remote_tags)
        self.local_path = local_path

    def do_backup(self):
        if not os.path.isdir(self.local_path) and os.path.exists(self.local_path):
            raise ValueError('%s exists and is not a directory' % self.local_path)
        elif not os.path.isdir(self.local_path):
            os.makedirs(self.local_path)
        for source in self.sources.values():
            source.backup()

    def get_cwd(self):
        return self.local_path


class GitRepository(FileRepository):
    def __init__(self, git_executable='git', local_path='.', local_tags='', included_remote_tags='',
                 excluded_remote_tags=''):
        super(GitRepository, self).__init__(local_path=local_path, local_tags=local_tags,
                                            included_remote_tags=included_remote_tags,
                                            excluded_remote_tags=excluded_remote_tags)
        self.git_executable = git_executable

    def do_backup(self):
        super(GitRepository, self).backup()
        end = datetime.datetime.now()
        subprocess.Popen([self.git_executable, 'init'], cwd=self.local_path)
        subprocess.Popen([self.git_executable, 'commit', '-am', end.strftime('Backup %Y/%m/%d %H:%M')],
                         cwd=self.local_path)
