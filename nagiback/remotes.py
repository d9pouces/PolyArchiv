# -*- coding=utf-8 -*-
from __future__ import unicode_literals
import logging

import subprocess

import datetime
try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urlparse import urlparse
import os

from nagiback.conf import Parameter, strip_split, check_executable, check_file, CheckOption
from nagiback.locals import GitRepository as LocalGitRepository, LocalRepository, FileRepository
from nagiback.repository import Repository, RepositoryInfo
from nagiback.utils import text_type, ensure_dir

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

    def backup(self, local_repository, force=False):
        """ perform the backup and log all errors
        """
        logger.info('remote backup %s of local repository %s' % (self.name, local_repository.name))
        info = self.get_info(local_repository)
        assert isinstance(info, RepositoryInfo)
        out_of_date = self.check_out_of_date_backup(current_time=datetime.datetime.now(),
                                                    previous_time=info.last_success)
        if not (force or out_of_date):
            # the last previous backup is still valid
            # => nothing to do
            logger.debug('last backup (%s) is still valid. No backup to do.' % info.last_success)
            return True
        elif info.last_success is None:
            logger.info('no previous remote backup: a new backup is required.')
        elif out_of_date:
            logger.info('last backup (%s) is out-of-date.' % str(info.last_success))
        elif force:
            logger.info('last backup (%s) is still valid but a new backup is forced.' % str(info.last_success))
        lock_ = None
        try:
            lock_ = local_repository.get_lock()
            self.do_backup(local_repository)
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
                local_repository.release_lock(lock_)
            except Exception as e:
                logger.critical('unable to release lock. %s' % str(e))
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
        subprocess.check_call(cmd, cwd=local_repository.local_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class Rsync(RemoteRepository):
    pass


def check_url(remote_url):
    """Check if the given URL starts by a valid scheme

    >>> check_url("scp://localhost/tmp")

    """
    parsed_url = urlparse(remote_url)
    if parsed_url.scheme not in ('http', 'https', 'scp', 'ftp', 'ftps', 'sftp', 'smb', 'file'):
        raise ValueError('Invalid scheme for remote URL: %s' % parsed_url.scheme)
    return remote_url


class TarArchive(RemoteRepository):

    excluded_files = {'.git', '.nagiback', '.gitignore'}
    parameters = RemoteRepository.parameters + [
        Parameter('tar_executable', converter=check_executable),
        Parameter('curl_executable', converter=check_executable),
        Parameter('remote_url', converter=check_url),
        Parameter('user'),
        Parameter('password'),
        Parameter('proxy'),
        Parameter('date_format'),
        Parameter('keytab', converter=check_file),
        Parameter('private_key', converter=check_file),
        Parameter('tar_format', converter=CheckOption(['tar.gz', 'tar.bz2', 'tar.xz']))
    ]

    def __init__(self, name, tar_executable='tar', curl_executable='curl', remote_url='', user='', password='',
                 keytab=None, tar_format='tar.xz', date_format='%Y-%m-%d_%H-%M', private_key=None, proxy=None, **kwargs):
        super(TarArchive, self).__init__(name, **kwargs)
        self.date_format = date_format
        self.tar_format = tar_format
        self.curl_executable = curl_executable
        self.tar_executable = tar_executable
        self.remote_url = remote_url
        self.user = user
        self.password = password
        self.keytab = keytab
        self.private_key = private_key
        self.proxy = proxy

    def do_backup(self, local_repository):
        assert isinstance(local_repository, FileRepository)
        error = None
        filenames = {x for x in os.listdir(local_repository.local_path)} - self.excluded_files
        filenames = [x for x in filenames]
        filenames.sort()
        now_str = datetime.datetime.now().strftime(self.date_format)
        archive_filename = os.path.join(local_repository.local_path, 'archive-%s.%s' % (now_str, self.tar_format))
        if self.tar_format == 'tar.gz':
            cmd = [self.tar_executable, 'czf']
        elif self.tar_format == 'tar.bz2':
            cmd = [self.tar_executable, 'cjf']
        elif self.tar_format == 'tar.xz':
            cmd = [self.tar_executable, 'cJf']
        else:
            raise ValueError('invalid tar format: %s' % self.tar_format)
        cmd.append(archive_filename)
        cmd += filenames
        logger.info(' '.join(cmd))
        p = subprocess.Popen(cmd, cwd=local_repository.local_path, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            logger.error(stdout.decode())
            logger.error(stderr.decode())
            error = ValueError('unable to create archive %s' % archive_filename)
        else:
            cmd = []
            if self.keytab:
                cmd += ['k5start', '-q', '-f', self.keytab, '-U', '--']
            if self.remote_url.startswith('file://'):
                ensure_dir(self.remote_url[7:], parent=False)
                cmd += ['cp', archive_filename, self.remote_url[7:]]
            else:
                cmd += [self.curl_executable, ]
                cmd += ['-u', '%s:%s' % (self.user, self.password)]
                if self.private_key:
                    cmd += ['--key', self.private_key]
                if self.proxy:
                    cmd += ['-x', self.proxy]
                cmd += ['-T', archive_filename]
                if self.remote_url.startswith('ftps'):
                    cmd += ['--ftp-ssl', 'ftp' + self.remote_url[4:]]
                else:
                    cmd += [self.remote_url]
            logger.info(' '.join(cmd))
            p = subprocess.Popen(cmd, cwd=local_repository.local_path, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                logger.error(stdout.decode())
                logger.error(stderr.decode())
                error = ValueError('unable to create archive %s' % archive_filename)

        if os.path.isfile(archive_filename):
            logger.info('remove %s' % archive_filename)
            os.remove(archive_filename)
        if error is not None:
            raise error
