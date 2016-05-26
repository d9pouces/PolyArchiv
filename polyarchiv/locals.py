# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import codecs
import datetime
import logging
import os
import re
import shutil
import subprocess

from polyarchiv.conf import Parameter, strip_split, check_directory, check_executable
from polyarchiv.filelocks import Lock
from polyarchiv.repository import Repository, RepositoryInfo
from polyarchiv.termcolor import RED
from polyarchiv.termcolor import cprint
from polyarchiv.utils import text_type

__author__ = 'mgallet'
logger = logging.getLogger('polyarchiv')


class LocalRepository(Repository):
    """Local repository, made of one or more sources.
     Each source is run and contribute to new
    """
    parameters = Repository.parameters + [
        Parameter('local_tags', converter=strip_split,
                  help_str='list of tags (comma-separated) associated to this local repository'),
        Parameter('included_remote_tags', converter=strip_split,
                  help_str='any remote repository with one of these tags (comma-separated) will be associated '
                           'to this local repo. You can use ? or * as jokers in these tags.'),
        Parameter('excluded_remote_tags', converter=strip_split,
                  help_str='any remote repository with one of these tags (comma-separated) will not be associated'
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
        self.variables = {}

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
            logger.info('last backup (%s) is still valid. No backup to do.' % info.last_success)
            return True
        elif info.last_success is None:
            logger.info('no previous backup: a new backup is required.')
        elif out_of_date:
            logger.info('last backup (%s) is out-of-date.' % str(info.last_success))
        elif force:
            logger.info('last backup (%s) is still valid but a new backup is forced.' % str(info.last_success))
        lock_ = None
        try:
            if self.can_execute_command(''):
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
            cprint('unable to perform backup: %s' % text_type(e), RED)
            info.fail_count += 1
            info.last_fail = datetime.datetime.now()
            info.last_state_valid = False
            info.last_message = text_type(e)

        if lock_ is not None:
            try:
                if self.can_execute_command(''):
                    self.release_lock(lock_)
            except Exception as e:
                cprint('unable to release lock. %s' % text_type(e), RED)
        if self.can_execute_command('# register this backup state'):
            self.set_info(info)
        return info.last_state_valid

    def restore(self):
        raise NotImplementedError

    def add_source(self, source):
        """
        :param source: source
        :type source: :class:`polyarchiv.sources.Source`
        """
        self.sources.append(source)

    @property
    def import_data_path(self):
        """Must return a valid directory where a source can write its files.
        If the local repository is not the filesystem, any file written in this directory by a source must be stored
        to the local repository's storage.
        """
        raise NotImplementedError

    @property
    def export_data_path(self):
        """Must return a valid directory, with all files to be read by remote repositories.
        If the local repository is not the filesystem, this directory must contain all files to be exported.
        """
        raise NotImplementedError

    @property
    def metadata_path(self):
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

    def get_info(self):
        raise NotImplementedError

    def set_info(self, info):
        raise NotImplementedError

    def get_lock(self):
        """Return a lock object, ensuring that only one instance of this repository is currently running"""
        raise NotImplementedError

    def release_lock(self, lock_):
        """Release the lock object provided by the above method"""
        raise NotImplementedError

    def remote_private_path(self, remote_repository):
        from polyarchiv.remotes import RemoteRepository
        assert isinstance(remote_repository, RemoteRepository)
        raise NotImplementedError


class FileRepository(LocalRepository):
    """Collect files from all sources in the folder 'local_path'.
    """

    parameters = LocalRepository.parameters + [
        Parameter('local_path', converter=check_directory, help_str='absolute path where all data are locally gathered')
    ]
    LAST_BACKUP_FILE = '.last-backup'
    METADATA_FOLDER = 'metadata'

    def __init__(self, name, local_path='.', **kwargs):
        super(FileRepository, self).__init__(name=name, **kwargs)
        self.local_path = local_path

    def pre_source_backup(self):
        self.ensure_dir(self.import_data_path)

    def post_source_backup(self):
        last_backup_date = RepositoryInfo.datetime_to_str(datetime.datetime.now())
        filename = os.path.join(self.import_data_path, self.LAST_BACKUP_FILE)
        if self.can_execute_command('echo \'%s\' > %s' % (last_backup_date, filename)):
            with codecs.open(filename, 'w', encoding='utf-8') as fd:
                fd.write(last_backup_date)

    @property
    def import_data_path(self):
        path = os.path.join(self.local_path, 'backups')
        self.ensure_dir(path)
        return path

    @property
    def export_data_path(self):
        return self.import_data_path

    @property
    def metadata_path(self):
        path = os.path.join(self.local_path, self.METADATA_FOLDER, 'local')
        self.ensure_dir(path)
        return path

    @property
    def lock_filepath(self):
        return os.path.join(self.metadata_path, 'lock')

    def remote_private_path(self, remote_repository):
        path = os.path.join(self.local_path, self.METADATA_FOLDER, 'remotes', remote_repository.name)
        return path

    def get_info(self):
        path = os.path.join(self.metadata_path, '%s.json' % self.name)
        self.ensure_dir(path, parent=True)
        if os.path.isfile(path):
            with codecs.open(path, 'r', encoding='utf-8') as fd:
                content = fd.read()
            return RepositoryInfo.from_str(content)
        else:
            return RepositoryInfo()

    def set_info(self, info):
        assert isinstance(info, RepositoryInfo)
        path = os.path.join(self.metadata_path, '%s.json' % self.name)
        self.ensure_dir(path, parent=True)
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

    def restore(self):
        raise NotImplementedError


class GitRepository(FileRepository):
    """Create a local git repository. Collect files from all sources and commit them locally.
    """
    parameters = FileRepository.parameters + [
        Parameter('git_executable', converter=check_executable, help_str='path of the git executable (default: "git")'),
        Parameter('commit_email', help_str='user email used for signing commits (default: "polyarchiv@19pouces.net")'),
        Parameter('commit_name', help_str='user name used for signing commits (default: "polyarchiv")'),
    ]

    def __init__(self, name, git_executable='git', commit_name='polyarchiv', commit_email='polyarchiv@19pouces.net',
                 **kwargs):
        super(GitRepository, self).__init__(name=name, **kwargs)
        self.commit_name = commit_name
        self.commit_email = commit_email
        self.git_executable = git_executable

    def post_source_backup(self):
        super(GitRepository, self).post_source_backup()
        path = os.path.join(self.local_path, '.gitignore')
        if not os.path.isfile(path) and self.can_execute_command('echo \'%s/\' > %s' % (self.METADATA_FOLDER, path)):
            with codecs.open(path, 'w', encoding='utf-8') as fd:
                fd.write("%s/\n" % self.METADATA_FOLDER)
        git_config_path = os.path.join(self.metadata_path, '.gitconfig')
        if not os.path.isfile(git_config_path):
            self.execute_command([self.git_executable, 'config', '--global', 'user.email', self.commit_email],
                                 env={'HOME': self.metadata_path})
            self.execute_command([self.git_executable, 'config', '--global', 'user.name', self.commit_name],
                                 env={'HOME': self.metadata_path})
        os.chdir(self.local_path)
        self.execute_command([self.git_executable, 'init'], cwd=self.local_path)
        self.execute_command([self.git_executable, 'add', '.'])
        end = datetime.datetime.now()
        # noinspection PyTypeChecker
        self.execute_command([self.git_executable, 'commit', '-am', end.strftime('Backup %Y/%m/%d %H:%M')],
                             ignore_errors=True, env={'HOME': self.metadata_path})

    def restore(self):
        raise NotImplementedError


def check_archive(value):
    if value.endswith('.tar.gz'):
        return value
    elif value.endswith('.tar.bz2'):
        return value
    elif value.endswith('.tar.xz'):
        return value
    raise ValueError('Archive name must end by .tar.gz, .tar.bz2 or .tar.xz')


class ArchiveRepository(FileRepository):
    """Create an archive (.tar.gz, .tar.xz or .tar.bz2) with files collected from all sources."""

    parameters = FileRepository.parameters + [
        Parameter('archive_name', converter=check_archive, help_str='Name of the created archive, must end by .tar.gz, '
                                                                    '.tar.bz2 or .tar.xz. Default to archive.tar.gz')
    ]

    def __init__(self, name, archive_name='archive.tar.gz', **kwargs):
        super(ArchiveRepository, self).__init__(name=name, **kwargs)
        self.archive_name = archive_name

    def post_source_backup(self):
        super(ArchiveRepository, self).post_source_backup()
        self.ensure_dir(self.export_data_path)
        compression = 'j'
        if self.archive_name.endswith('.tar.gz'):
            compression = 'z'
        elif self.archive_name.endswith('.tar.xz'):
            compression = 'x'
        file_list = os.listdir(self.import_data_path)
        if file_list:
            self.execute_command(['tar', '-c%sf' % compression, os.path.join(self.export_data_path, self.archive_name)
                                  ] + file_list,
                                 cwd=self.import_data_path)
        if self.can_execute_command(['rm', '-rf', self.import_data_path]):
            shutil.rmtree(self.import_data_path)

    @property
    def export_data_path(self):
        return os.path.join(self.local_path, 'archives')

    def restore(self):
        raise NotImplementedError
