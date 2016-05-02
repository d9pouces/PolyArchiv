# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import codecs
import datetime
import logging
import os
import subprocess
import re

from nagiback.conf import Parameter, strip_split, check_directory, check_executable
from nagiback.filelocks import Lock
from nagiback.repository import Repository, RepositoryInfo
from nagiback.utils import ensure_dir, text_type

__author__ = 'mgallet'
logger = logging.getLogger('nagiback.sources')


class LocalRepository(Repository):
    """Local repository, made of one or more sources.
     Each source is run and contribute to new
    """
    parameters = Repository.parameters + [
        Parameter('local_tags', converter=strip_split,
                  help_str='List of tags (comma-separated) associated to this local repository'),
        Parameter('included_remote_tags', converter=strip_split,
                  help_str='Any remote repository with one of these tags (comma-separated) will be associated '
                           'to this local repo. You can use ? or * as jokers in these tags.'),
        Parameter('excluded_remote_tags', converter=strip_split,
                  help_str='Any remote repository with one of these tags (comma-separated) will not be associated'
                           ' to this local repo. You can use ? or * as jokers in these tags. Have precedence over '
                           'included_local_tags and included_remote_tags.'),
    ]

    def __init__(self, name, local_tags=None, included_remote_tags=None, excluded_remote_tags=None,
                 **kwargs):
        super(LocalRepository, self).__init__(name=name, **kwargs)
        self.local_tags = ['local'] if local_tags is None else local_tags
        self.included_remote_tags = ['*'] if included_remote_tags is None else included_remote_tags
        self.excluded_remote_tags = excluded_remote_tags or []
        self.sources = []

    def backup(self, force=False):
        """ perform the backup and log all errors
        """
        logger.info('backup of local repository %s' % self.name)
        info = self.get_info()
        assert isinstance(info, RepositoryInfo)
        out_of_date = self.check_out_of_date_backup(current_time=datetime.datetime.now(),
                                                    previous_time=info.last_success)
        if not (force or out_of_date):
            # the last previous backup is still valid
            # => nothing to do
            logger.debug('last backup (%s) is still valid. No backup to do.' % info.last_success)
            return True
        elif info.last_success is None:
            logger.info('no previous backup: a new backup is required.')
        elif out_of_date:
            logger.info('last backup (%s) is out-of-date.' % str(info.last_success))
        elif force:
            logger.info('last backup (%s) is still valid but a new backup is forced.' % str(info.last_success))
        lock_ = None
        try:
            lock_ = self.get_lock()
            self.pre_source_backup()
            for source in self.sources:
                source.backup()
            self.post_source_backup()
            info.total_size = self.get_repository_size()
            info.success_count += 1
            info.last_state_valid = True
            info.last_success = datetime.datetime.now()
            info.last_message = 'ok'
        except Exception as e:
            logger.exception('unable to perform backup', exc_info=e)
            info.fail_count += 1
            info.last_fail = datetime.datetime.now()
            info.last_state_valid = False
            info.last_message = text_type(e)

        if lock_ is not None:
            try:
                self.release_lock(lock_)
            except Exception as e:
                logger.critical('unable to release lock. %s' % str(e))
        self.set_info(info)
        return info.last_state_valid

    def restore(self):
        raise NotImplementedError

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

    def pre_source_backup(self):
        raise NotImplementedError

    def post_source_backup(self):
        raise NotImplementedError

    def get_repository_size(self):
        """ return the size of the repository (in bytes)
        :return:
        :rtype:
        """
        raise NotImplementedError

    def get_info(self, name=None, kind='local'):
        raise NotImplementedError

    def set_info(self, info, name=None, kind='local'):
        raise NotImplementedError

    def get_lock(self):
        """Return a lock object, ensuring that only one instance of this repository is currently running"""
        raise NotImplementedError

    def release_lock(self, lock_):
        """Release the lock object provided by the above method"""
        raise NotImplementedError


class FileRepository(LocalRepository):
    """
    example structure:
        dir/some/files
        database-dump.sql
        .nagiback/lock
        .nagiback/local/global.json
        .nagiback/remote/my_remote.json
    """
    parameters = LocalRepository.parameters + [
        Parameter('local_path', converter=check_directory, help_str='absolute path to locally gather all data')
    ]
    LAST_BACKUP_FILE = '.last-backup'
    PRIVATE_FOLDER = '.nagiback'

    def __init__(self, name, local_path='.', **kwargs):
        super(FileRepository, self).__init__(name=name, **kwargs)
        self.local_path = local_path

    def pre_source_backup(self):
        ensure_dir(self.local_path)

    def post_source_backup(self):
        last_backup_date = RepositoryInfo.datetime_to_str(datetime.datetime.now())
        with codecs.open(os.path.join(self.local_path, self.LAST_BACKUP_FILE), 'w', encoding='utf-8') as fd:
            fd.write(last_backup_date)

    def get_cwd(self):
        ensure_dir(self.local_path)
        return self.local_path

    @property
    def private_path(self):
        return os.path.join(self.local_path, self.PRIVATE_FOLDER)

    @property
    def lock_filepath(self):
        return os.path.join(self.private_path, 'lock')

    def get_info(self, name=None, kind='local'):
        if name is None:
            name = self.name
        path = os.path.join(self.private_path, kind, '%s.json' % name)
        ensure_dir(path, parent=True)
        if os.path.isfile(path):
            with codecs.open(path, 'r', encoding='utf-8') as fd:
                content = fd.read()
            return RepositoryInfo.from_str(content)
        else:
            return RepositoryInfo()

    def set_info(self, info, name=None, kind='local'):
        if name is None:
            name = self.name
        assert isinstance(info, RepositoryInfo)
        path = os.path.join(self.private_path, kind, '%s.json' % name)
        ensure_dir(path, parent=True)
        content = info.to_str()
        with codecs.open(path, 'w', encoding='utf-8') as fd:
            fd.write(content)

    def get_lock(self):
        lock_ = Lock(self.lock_filepath)
        if lock_.acquire(timeout=1):
            return lock_
        else:
            logger.error('Unable to lock local repository. Check if no other backup is currently running or '
                         'delete %s' % self.lock_filepath)
            raise ValueError

    def get_repository_size(self):
        content = subprocess.check_output(['du', '-s'], cwd=self.local_path).decode()
        matcher = re.match('^(\d+) \.$', content.strip())
        if not matcher:
            return 0
        return int(matcher.group(1))

    def release_lock(self, lock_):
        lock_.release()


class GitRepository(FileRepository):
    parameters = FileRepository.parameters + [
        Parameter('git_executable', converter=check_executable, help_str='path of the git executable (default: "git")'),
    ]

    def __init__(self, name, git_executable='git', **kwargs):
        super(GitRepository, self).__init__(name=name, **kwargs)
        self.git_executable = git_executable

    def post_source_backup(self):
        super(GitRepository, self).post_source_backup()
        gitignore = os.path.join(self.local_path, '.gitignore')
        if not os.path.isfile(gitignore):
            with codecs.open(gitignore, 'w', encoding='utf-8') as fd:
                fd.write("%s/\n" % self.PRIVATE_FOLDER)

        cmd = [self.git_executable, 'init']
        logger.info(' '.join(cmd))
        p = subprocess.Popen(cmd, cwd=self.local_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            logger.error(stdout.decode())
            logger.error(stderr.decode())
            raise ValueError()

        cmd = [self.git_executable, 'add', '.']
        logger.info(' '.join(cmd))
        p = subprocess.Popen(cmd, cwd=self.local_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            logger.error(stdout.decode())
            logger.error(stderr.decode())
            raise ValueError()

        end = datetime.datetime.now()
        cmd = [self.git_executable, 'commit', '-am', end.strftime('Backup %Y/%m/%d %H:%M')]
        logger.info(' '.join(cmd))
        p = subprocess.Popen(cmd, cwd=self.local_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
