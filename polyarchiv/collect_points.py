# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import codecs
import datetime
import os
import re
import shutil
import subprocess
import tarfile

# noinspection PyProtectedMember
from polyarchiv._vendor.lru_cache import lru_cache
from polyarchiv.conf import Parameter, strip_split, check_directory
from polyarchiv.config_checks import ValidSvnUrl
from polyarchiv.filelocks import Lock
from polyarchiv.hooks import Hook
from polyarchiv.points import Point, PointInfo
from polyarchiv.utils import text_type, cached_property, url_auth_split, DEFAULT_EMAIL, DEFAULT_USERNAME

__author__ = 'Matthieu Gallet'


class CollectPoint(Point):
    """Collect point, made of one or more sources.
     Each source is run and contribute to new
    """
    parameters = Point.parameters + [
        Parameter('collect_point_tags', converter=strip_split,
                  help_str='list of tags (comma-separated) associated to this collect point. Default: "collect"'),
        Parameter('included_backup_point_tags', converter=strip_split,
                  help_str='any backup point with one of these tags (comma-separated) will be associated '
                           'to this local repo. You can use ? or * as jokers in these tags. Default: "*"'),
        Parameter('excluded_backup_point_tags', converter=strip_split,
                  help_str='any backup point with one of these tags (comma-separated) will not be associated'
                           ' to this local repo. You can use ? or * as jokers in these tags. Have precedence over '
                           'included_collect_point_tags and included_backup_point_tags.'),
    ]
    checks = []

    # list of callable(runner, collect_point, backup_points)

    def __init__(self, name, collect_point_tags=None, included_backup_point_tags=None, excluded_backup_point_tags=None,
                 **kwargs):
        super(CollectPoint, self).__init__(name=name, **kwargs)
        self.collect_point_tags = ['collect'] if collect_point_tags is None else collect_point_tags
        self.included_backup_point_tags = ['*'] if included_backup_point_tags is None else included_backup_point_tags
        self.excluded_backup_point_tags = excluded_backup_point_tags or []
        self.sources = []
        # self.last_backup_file = last_backup_file

    def backup(self, force=False):
        """ perform the backup and log all errors
        """
        self.print_info('backup of collect point %s' % self.name)
        info = self.get_info()
        assert isinstance(info, PointInfo)
        out_of_date = self.check_out_of_date_backup(current_time=datetime.datetime.now(),
                                                    previous_time=info.last_success)
        if not (force or out_of_date):
            # the last previous backup is still valid
            # => nothing to do
            self.print_success('last backup (%s) is still valid. No backup to do.' % info.last_success)
            return True
        elif info.last_success is None:
            self.print_info('no previous backup: a new backup is required.')
        elif out_of_date:
            self.print_info('last backup (%s) is out-of-date.' % str(info.last_success))
        elif force:
            self.print_info('last backup (%s) is still valid but a new backup is forced.' % str(info.last_success))
        lock_ = None
        cwd = os.getcwd()
        try:
            if self.can_execute_command(''):
                lock_ = self.get_lock()
            self.pre_source_backup()
            for source in self.sources:
                source.backup()
            self.post_source_backup()

            next_path = self.private_data_path
            for filter_ in self.filters:
                next_path = filter_.backup(next_path, self.filter_private_path(filter_), allow_in_place=True)

            info.total_size = self.get_repository_size()
            info.success_count += 1
            info.last_state_valid = True
            info.last_success = datetime.datetime.now()
            info.last_message = 'ok'
        except Exception as e:
            self.print_error('unable to perform backup: %s' % text_type(e))
            info.fail_count += 1
            info.last_fail = datetime.datetime.now()
            info.last_state_valid = False
            info.last_message = text_type(e)
        finally:
            os.chdir(cwd)

        if lock_ is not None:
            try:
                if self.can_execute_command(''):
                    self.release_lock(lock_)
            except Exception as e:
                self.print_error('unable to release lock. %s' % text_type(e))
        if self.can_execute_command('# register this backup state'):
            self.set_info(info)
        return info.last_state_valid

    def restore(self):
        next_path = self.private_data_path
        filter_data = []
        for filter_ in self.filters:
            filter_data.append((filter_, next_path))
            next_path = filter_.next_path(next_path, self.filter_private_path(filter_), allow_in_place=True)
        for filter_, next_path in reversed(filter_data):
            filter_.restore(next_path, self.filter_private_path(filter_), allow_in_place=True)

        self.pre_source_restore()
        for source in self.sources:
            source.restore()
        self.post_source_restore()

    def add_source(self, source):
        """
        :param source: source
        :type source: :class:`polyarchiv.sources.Source`
        """
        self.sources.append(source)

    @property
    def import_data_path(self):
        """Must return a valid directory where a source can write its files.
        If the collect point is not the filesystem, any file written in this directory by a source must be stored
        to the collect point's storage.
        """
        raise NotImplementedError

    @property
    def private_data_path(self):
        """where all exported data are actually stored and where the first filter are applied"""
        raise NotImplementedError

    @cached_property
    def export_data_path(self):
        """exported data by the last filter"""
        from polyarchiv.filters import FileFilter
        next_path = self.private_data_path
        for filter_ in self.filters:
            assert isinstance(filter_, FileFilter)
            next_path = filter_.next_path(next_path, self.filter_private_path(filter_), allow_in_place=True)
        return next_path

    @property
    def metadata_path(self):
        raise NotImplementedError

    def pre_source_backup(self):
        """called before the first source backup"""
        pass

    def post_source_backup(self):
        """called after the last source backup"""
        pass

    def pre_source_restore(self):
        """called before the first source restore"""
        pass

    def post_source_restore(self):
        """called after the last source restore"""
        pass

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

    def backup_point_private_path(self, backup_point):
        from polyarchiv.backup_points import BackupPoint
        assert isinstance(backup_point, BackupPoint)
        raise NotImplementedError

    def filter_private_path(self, filter_):
        from polyarchiv.filters import FileFilter
        assert isinstance(filter_, FileFilter)
        raise NotImplementedError

    def execute_hook(self, when, cm, result=None):
        result_ = {self.name: result}
        for hook in self.hooks:
            assert isinstance(hook, Hook)
            if when in hook.hooked_events:
                hook.call(when, cm, result_, {})


class FileRepository(CollectPoint):
    """Collect files from all sources in the folder 'local_path'.
    """

    parameters = CollectPoint.parameters + [
        Parameter('local_path', converter=check_directory, required=True,
                  help_str='absolute path where all data are locally gathered [*]')
    ]
    METADATA_FOLDER = 'metadata'

    def __init__(self, name, local_path='.', **kwargs):
        super(FileRepository, self).__init__(name=name, **kwargs)
        self.local_path = local_path

    def pre_source_backup(self):
        self.ensure_dir(self.import_data_path)

    @cached_property
    def import_data_path(self):
        path = self.format_value(os.path.join(self.local_path, 'backups'))
        return path

    @cached_property
    def private_data_path(self):
        """where all exported data are actually stored"""
        return self.import_data_path

    @cached_property
    def metadata_path(self):
        path = os.path.join(self.local_path, self.METADATA_FOLDER, 'collect_point')
        path = self.format_value(path)
        self.ensure_dir(path)
        return path

    @cached_property
    def lock_filepath(self):
        return os.path.join(self.metadata_path, 'lock')

    @lru_cache()
    def backup_point_private_path(self, backup_point):
        path = os.path.join(self.local_path, self.METADATA_FOLDER, 'remote-%s' % backup_point.name)
        return self.format_value(path)

    @lru_cache()
    def filter_private_path(self, filter_):
        path = os.path.join(self.local_path, self.METADATA_FOLDER, 'filter-%s' % filter_.name)
        return self.format_value(path)

    def get_info(self):
        path = os.path.join(self.metadata_path, '%s.json' % self.name)
        self.ensure_dir(path, parent=True)
        if os.path.isfile(path):
            with codecs.open(path, 'r', encoding='utf-8') as fd:
                content = fd.read()
            return PointInfo.from_str(content)
        else:
            return PointInfo()

    def set_info(self, info):
        assert isinstance(info, PointInfo)
        path = os.path.join(self.metadata_path, '%s.json' % self.name)
        self.ensure_dir(path, parent=True)
        content = info.to_str()
        with codecs.open(path, 'w', encoding='utf-8') as fd:
            fd.write(content)

    def get_lock(self):
        self.ensure_dir(self.lock_filepath, parent=True)
        lock_ = Lock(self.lock_filepath)
        if lock_.acquire(timeout=1):
            return lock_
        else:
            self.print_error('Unable to lock collect point. Check if no other backup is currently running or '
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

    def pre_source_restore(self):
        pass

    def post_source_restore(self):
        pass


class GitRepository(FileRepository):
    """Create a local git repository. Collect files from all sources and commit them locally.
    """
    parameters = FileRepository.parameters + [
        Parameter('commit_email', help_str='user email used for signing commits (default: "%s") [*]' % DEFAULT_EMAIL),
        Parameter('commit_name', help_str='user name used for signing commits (default: "%s") [*]' % DEFAULT_USERNAME),
        Parameter('commit_message', help_str='commit message (default: "Backup {Y}/{m}/{d} {H}:{M}") [*]'),
    ]

    def __init__(self, name, commit_name=DEFAULT_USERNAME, commit_email=DEFAULT_EMAIL,
                 commit_message='Backup {Y}/{m}/{d} {H}:{M}', **kwargs):
        super(GitRepository, self).__init__(name=name, **kwargs)
        self.commit_name = commit_name
        self.commit_email = commit_email
        self.commit_message = commit_message

    def post_source_backup(self):
        super(GitRepository, self).post_source_backup()
        git_config_path = os.path.join(self.metadata_path, '.gitconfig')
        if not os.path.isfile(git_config_path):
            self.execute_command([self.config.git_executable, 'config', '--global', 'user.email',
                                  self.format_value(self.commit_email)], env={'HOME': self.metadata_path})
            self.execute_command([self.config.git_executable, 'config', '--global', 'user.name',
                                  self.format_value(self.commit_name)], env={'HOME': self.metadata_path})
        os.chdir(self.import_data_path)
        self.execute_command([self.config.git_executable, 'init'], cwd=self.import_data_path)
        self.execute_command([self.config.git_executable, 'add', '.'])
        self.execute_command([self.config.git_executable, 'commit', '-am', self.format_value(self.commit_message)],
                             ignore_errors=True, env={'HOME': self.metadata_path})

    def pre_source_restore(self):
        os.chdir(self.import_data_path)
        self.execute_command([self.config.git_executable, 'reset', '--hard'], cwd=self.import_data_path,
                             env={'HOME': self.metadata_path})
        self.execute_command([self.config.git_executable, 'clean', '-f'], cwd=self.import_data_path,
                             env={'HOME': self.metadata_path})


def check_archive(value):
    if value.endswith('.tar.gz') or value.endswith('.tar.bz2') or value.endswith('.tar.xz'):
        return value
    raise ValueError('Archive name must end by .tar.gz, .tar.bz2 or .tar.xz')


class ArchiveRepository(FileRepository):
    """Create an archive (.tar.gz, .tar.xz or .tar.bz2) with files collected from all sources."""

    parameters = FileRepository.parameters + [
        Parameter('archive_name', converter=check_archive, help_str='Name of the created archive, must end by .tar.gz, '
                                                                    '.tar.bz2 or .tar.xz. Default: "archive.tar.gz"[*]')
    ]

    def __init__(self, name, archive_name='archive.tar.gz', **kwargs):
        super(ArchiveRepository, self).__init__(name=name, **kwargs)
        self.archive_name = archive_name

    def post_source_backup(self):
        super(ArchiveRepository, self).post_source_backup()
        self.ensure_dir(self.private_data_path)
        comp = 'j'
        archive_name = self.format_value(self.archive_name)
        if archive_name.endswith('.tar.gz'):
            comp = 'z'
        elif archive_name.endswith('.tar.xz'):
            comp = 'x'
        file_list = os.listdir(self.import_data_path)
        full_path = os.path.join(self.private_data_path, archive_name)
        if file_list:
            self.execute_command(['tar', '-c%sf' % comp, full_path] + file_list, cwd=self.import_data_path)
        elif self.can_execute_command(['tar', '-c%sf' % comp, full_path]):
            mode = {'j': 'w:bz2', 'x': 'w:xz', 'z': 'w:gz'}[comp]
            tarfile.open(name=full_path, mode=mode).close()
        if self.can_execute_command(['rm', '-rf', self.import_data_path]):
            shutil.rmtree(self.import_data_path)

    @property
    def private_data_path(self):
        path = os.path.join(self.local_path, 'archives')
        return self.format_value(path)

    def pre_source_restore(self):
        archive_name = self.format_value(self.archive_name)
        full_path = os.path.join(self.private_data_path, archive_name)
        path = self.import_data_path
        if (os.path.isdir(path) and os.listdir(path)) and self.can_execute_command(['rm', '-rf', path]):
            shutil.rmtree(path)
        self.ensure_dir(path)
        self.execute_command(['tar', '-C', path, '-xf', full_path])


class SvnRepository(FileRepository):
    """Collect files from all sources in the folder 'local_path' and commit them to a remote SVN repository.
    """

    parameters = FileRepository.parameters + [
        Parameter('remote_url', required=True,
                  help_str='URL of the remote repository (must exist). Should contain username and password [*]'),
        Parameter('ca_cert', help_str='CA certificate associated to \'remote_url\'. '
                                      'Set to "any" for not checking certificates [*]'),
        Parameter('client_cert', help_str='Client certificate associated to \'remote_url\' [*]'),
        Parameter('client_cert_password', help_str='Password for encrypted client certificates [*]'),
        Parameter('commit_message', help_str='commit message (default: "Backup {Y}/{m}/{d} {H}:{M}") [*]'),
    ]
    checks = FileRepository.checks + [ValidSvnUrl('remote_url')]

    def __init__(self, name, remote_url=None, ca_cert=None, client_cert=None, client_cert_password=None,
                 commit_message='Backup {Y}/{m}/{d} {H}:{M}', **kwargs):
        super(SvnRepository, self).__init__(name=name, **kwargs)
        remote_url, username, password = url_auth_split(self.format_value(remote_url))
        self.username = username
        self.password = password
        self.ca_cert = ca_cert
        self.remote_url = remote_url
        self.client_cert = client_cert
        self.commit_message = commit_message
        self.client_cert_password = client_cert_password

    @cached_property
    def svn_folder(self):
        return os.path.join(self.import_data_path, '.svn')

    def release_lock(self, lock_):
        lock_.release()

    def pre_source_backup(self):
        if not os.path.isdir(self.svn_folder):
            cmd = [self.config.svn_executable, 'co', '--ignore-externals', '--force', ]
            cmd += self.__svn_parameters()
            cmd += [self.remote_url, self.import_data_path]
            self.execute_command(cmd)

    def post_source_backup(self):
        cmd = [self.config.svn_executable, 'status']
        p = subprocess.Popen(cmd, cwd=self.import_data_path, stdout=subprocess.PIPE, stderr=open(os.devnull, 'wb'))
        stdout, stderr = p.communicate()
        to_add = []
        to_remove = []
        for line in stdout.decode('utf-8').splitlines():
            matcher = re.match(r'^([ ADMRCXI?!~])[ MC][ L][ +][ S][ KOTB][ C] (?P<name>.*)$', line)
            if not matcher:
                continue
            status, name = matcher.groups()
            if status == '?':
                to_add.append(name)
            elif status == '!':
                to_remove.append(name)
        if to_add:
            self.execute_command([self.config.svn_executable, 'add'] + to_add, cwd=self.import_data_path)
        if to_remove:
            self.execute_command([self.config.svn_executable, 'rm', '--force'] + to_remove, cwd=self.import_data_path)
        message = self.format_value(self.commit_message)
        cmd = [self.config.svn_executable, 'ci', '-m', message]
        cmd += self.__svn_parameters()
        self.execute_command(cmd, cwd=self.import_data_path)

    def __svn_parameters(self):
        result = ['--non-interactive', '--no-auth-cache']
        if self.username:
            result += ['--username', self.username]
        if self.password:
            result += ['--password', self.password]
        ca_cert = self.format_value(self.ca_cert)
        if ca_cert == 'any':
            result += ['--trust-server-cert']
        elif ca_cert:
            result += ['--config-option', 'servers:global:ssl-authority-files=%s' % ca_cert]
        client_cert = self.format_value(self.client_cert)
        if client_cert:
            result += ['--config-option',
                       'servers:global:ssl-client-cert-file=%s' % client_cert]
        client_cert_password = self.format_value(self.client_cert_password)
        if client_cert_password:
            result += ['--config-option',
                       'servers:global:ssl-client-cert-password=%s' % client_cert_password]
        return result

    def pre_source_restore(self):
        self.pre_source_backup()
        cmd = [self.config.svn_executable, 'up', '-r', 'HEAD', '--ignore-externals', '--force', '--accept',
               'theirs-conflict', ]
        cmd += self.__svn_parameters()
        self.execute_command(cmd, cwd=self.import_data_path)
