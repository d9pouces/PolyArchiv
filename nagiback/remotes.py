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

from nagiback.conf import Parameter, strip_split, check_executable, check_file, CheckOption, bool_setting
from nagiback.locals import GitRepository as LocalGitRepository, LocalRepository, FileRepository
from nagiback.repository import Repository, RepositoryInfo
from nagiback.utils import text_type, ensure_dir

__author__ = 'mgallet'
logger = logging.getLogger('nagiback.remotes')


class RemoteRepository(Repository):
    parameters = Repository.parameters + [
        Parameter('remote_tags', converter=strip_split,
                  help_str='List of tags (comma-separated) associated to this remote repository'),
        Parameter('included_local_tags', converter=strip_split,
                  help_str='Any local repository with one of these tags (comma-separated) will be associated '
                           'to this remote repo. You can use ? or * as jokers in these tags.'),
        Parameter('excluded_local_tags', converter=strip_split,
                  help_str='Any local repository with one of these tags (comma-separated) will not be associated'
                           ' to this remote repo. You can use ? or * as jokers in these tags. Have precedence over '
                           'included_local_tags and included_remote_tags.'),
    ]

    def __init__(self, name, remote_tags=None, included_local_tags=None, excluded_local_tags=None, **kwargs):
        super(RemoteRepository, self).__init__(name, **kwargs)
        self.remote_tags = ['remote'] if remote_tags is None else remote_tags
        self.included_local_tags = ['*'] if included_local_tags is None else included_local_tags
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


def check_git_url(remote_url):
    """Check if the given URL starts by a valid scheme

    >>> check_git_url("http://localhost/tmp.git") == 'http://localhost/tmp.git'
    True

    """
    parsed_url = urlparse(remote_url)
    if parsed_url.scheme not in ('http', 'https', 'git'):
        raise ValueError('Invalid scheme for remote URL: %s' % parsed_url.scheme)
    return remote_url


class GitRepository(RemoteRepository):
    parameters = RemoteRepository.parameters + [
        Parameter('git_executable', converter=check_executable, help_str='path of the git executable (default: "git")'),
        Parameter('remote_url', help_str='URL of the remote server, include username and password (e.g.: '
                                         'git@mygitlab.example.org:username/project.git,'
                                         'https://username:password@mygitlab.example.org/username/project.git)'),
        Parameter('remote_branch', help_str='name of the remote branch'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication)'),
        Parameter('private_key', converter=check_file,
                  help_str='absolute path of the private key file (for SSH key authentication)'),
    ]

    def __init__(self, name, remote_url='', remote_branch='master', git_executable='git',
                 keytab=None, private_key=None, **kwargs):
        super(GitRepository, self).__init__(name, **kwargs)
        self.keytab = keytab
        self.private_key = private_key
        self.remote_url = remote_url
        self.remote_branch = remote_branch
        self.git_executable = git_executable

    def do_backup(self, local_repository):
        assert local_repository.__class__ == LocalGitRepository
        assert isinstance(local_repository, LocalGitRepository)
        cmd = []
        if self.keytab:
            cmd += ['k5start', '-q', '-f', self.keytab, '-U', '--']
        cmd += [self.git_executable, 'push', self.remote_url, '+master:%s' % self.remote_branch]
        if self.private_key and not self.remote_url.startswith('http'):
            cmd = ['ssh-agent', 'bash', '-c', 'ssh-add %s ; %s' % (self.private_key, ' '.join(cmd))]
        logger.info(' '.join(cmd))
        p = subprocess.Popen(cmd, cwd=local_repository.local_path, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            logger.error(stdout.decode())
            logger.error(stderr.decode())
            raise ValueError('unable to push to remote %s from %s' % (self.name, local_repository.local_path))


class Rsync(RemoteRepository):
    parameters = RemoteRepository.parameters + [
        Parameter('rsync_executable', converter=check_executable,
                  help_str='path of the rsync executable (default: "rsync")'),
        Parameter('remote_url', help_str='remote server and path (e.g. login:password@server:/foo/bar/'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication)'),
        Parameter('private_key', converter=check_file,
                  help_str='absolute path of the private key file (for SSH key authentication)'),
    ]

    def __init__(self, name, rsync_executable='tar', remote_url='', keytab=None, private_key=None, **kwargs):
        super(Rsync, self).__init__(name, **kwargs)
        self.rsync_executable = rsync_executable
        self.remote_url = remote_url
        self.keytab = keytab
        self.private_key = private_key

    def do_backup(self, local_repository):
        assert isinstance(local_repository, FileRepository)
        cmd = []
        if self.keytab:
            cmd += ['k5start', '-q', '-f', self.keytab, '-U', '--']
        cmd += [self.rsync_executable, '-az', '--delete', '-S']
        local_path = local_repository.local_path
        if not local_path.endswith(os.path.sep):
            local_path += os.path.sep
        remote_url = self.remote_url
        if not remote_url.endswith(os.path.sep):
            remote_url += os.path.sep
        if self.private_key:
            cmd += ['ssh -i %s' % self.private_key]
        else:
            cmd += ['ssh']
        cmd += [local_path, remote_url]
        logger.info(' '.join(cmd))
        p = subprocess.Popen(cmd, cwd=local_repository.local_path, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            logger.error(stdout.decode())
            logger.error(stderr.decode())
            raise ValueError('unable to synchronize %s against %s' % (local_path, remote_url))


def check_curl_url(remote_url):
    """Check if the given URL starts by a valid scheme

    >>> check_curl_url("scp://localhost/tmp") == 'scp://localhost/tmp'
    True

    """
    parsed_url = urlparse(remote_url)
    if parsed_url.scheme not in ('http', 'https', 'scp', 'ftp', 'ftps', 'sftp', 'smb', 'file'):
        raise ValueError('Invalid scheme for remote URL: %s' % parsed_url.scheme)
    return remote_url


class TarArchive(RemoteRepository):
    excluded_files = {'.git', '.nagiback', '.gitignore'}
    parameters = RemoteRepository.parameters + [
        Parameter('tar_executable', converter=check_executable,
                  help_str='path of the rsync executable (default: "tar")'),
        Parameter('curl_executable', converter=check_executable,
                  help_str='path of the rsync executable (default: "curl")'),
        Parameter('remote_url', converter=check_curl_url,
                  help_str='destination URL (e.g.: ftp://example.org/path/,'
                           'https://example.org/path)'),
        Parameter('user', help_str='username'),
        Parameter('password', help_str='password'),
        Parameter('archive_prefix', help_str='prefix of the archive names (default: "archive")'),
        Parameter('proxy', help_str='use this proxy for connections (e.g. username:password@proxy.example.org:8080)'),
        Parameter('insecure', converter=bool_setting, help_str='do not check certificate for SSL connections'),
        Parameter('cacert', converter=check_file, help_str='certificate to use to verify the server'),
        Parameter('date_format', help_str='date format for the generated archives (default: "%Y-%m-%d_%H-%M")'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication)'),
        Parameter('private_key', converter=check_file,
                  help_str='absolute path of the private key file (for SSH key authentication)'),
        Parameter('tar_format', converter=CheckOption(['tar.gz', 'tar.bz2', 'tar.xz']),
                  help_str='one of "tar.gz", "tar.bz2" (default), "tar.xz"')
    ]

    def __init__(self, name, tar_executable='tar', curl_executable='curl', remote_url='', user='', password='',
                 insecure=False, cacert=None, archive_prefix='archive',
                 keytab=None, private_key=None, tar_format='tar.bz2', date_format='%Y-%m-%d_%H-%M', proxy=None,
                 **kwargs):
        super(TarArchive, self).__init__(name, **kwargs)
        self.date_format = date_format
        self.archive_prefix = archive_prefix
        self.tar_format = tar_format
        self.curl_executable = curl_executable
        self.tar_executable = tar_executable
        self.remote_url = remote_url
        self.user = user
        self.password = password
        self.keytab = keytab
        self.private_key = private_key
        self.proxy = proxy
        self.insecure = insecure
        self.cacert = cacert

    def do_backup(self, local_repository):
        assert isinstance(local_repository, FileRepository)
        error = None
        filenames = {x for x in os.listdir(local_repository.local_path)} - self.excluded_files
        filenames = [x for x in filenames]
        filenames.sort()
        now_str = datetime.datetime.now().strftime(self.date_format)
        archive_filename = os.path.join(local_repository.local_path,
                                        '%s-%s.%s' % (self.archive_prefix, now_str, self.tar_format))
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
                cmd += [self.curl_executable, '--anyauth']
                if self.insecure:
                    cmd += ['-k']
                if self.cacert:
                    cmd += ['--cacert', self.cacert]
                cmd += ['-u', '%s:%s' % (self.user, self.password)]
                if self.private_key:
                    cmd += ['--key', self.private_key]
                if self.proxy:
                    cmd += ['-x', self.proxy, '--proxy-anyauth']
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
