# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import codecs
import datetime
import logging
import shutil


# noinspection PyProtectedMember
from polyarchiv._vendor import requests
# noinspection PyProtectedMember
from polyarchiv._vendor.lru_cache import lru_cache
from polyarchiv.backends import get_backend, StorageBackend
from polyarchiv.filters import FileFilter
from polyarchiv.param_checks import check_git_url, check_curl_url
from polyarchiv.termcolor import YELLOW, RED
from polyarchiv.termcolor import cprint

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse, urlencode, quote_plus
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urlparse import urlparse
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib import urlencode, quote_plus
import os

from polyarchiv.conf import Parameter, strip_split, check_executable, check_file, CheckOption, bool_setting
from polyarchiv.locals import LocalRepository
from polyarchiv.repository import Repository, RepositoryInfo
from polyarchiv.utils import text_type, ensure_dir

__author__ = 'Matthieu Gallet'
logger = logging.getLogger('polyarchiv.remotes')
constant_time = datetime.datetime(2016, 1, 1, 0, 0, 0)


class RemoteRepository(Repository):
    constant_format_values = {x: constant_time.strftime('%' + x) for x in 'aAwdbBmyYHIpMSfzZjUWcxX'}
    constant_format_values.update({'fqdn': 'localhost', 'hostname': 'localhost'})
    parameters = Repository.parameters + [
        Parameter('remote_tags', converter=strip_split,
                  help_str='list of tags (comma-separated) associated to this remote repository'),
        Parameter('included_local_tags', converter=strip_split,
                  help_str='any local repository with one of these tags (comma-separated) will be associated '
                           'to this remote repo. You can use ? or * as jokers in these tags.'),
        Parameter('excluded_local_tags', converter=strip_split,
                  help_str='any local repository with one of these tags (comma-separated) will not be associated'
                           ' to this remote repo. You can use ? or * as jokers in these tags. Have precedence over '
                           'included_local_tags and included_remote_tags.'),
    ]

    def __init__(self, name, remote_tags=None, included_local_tags=None, excluded_local_tags=None, **kwargs):
        super(RemoteRepository, self).__init__(name, **kwargs)
        self.remote_tags = ['remote'] if remote_tags is None else remote_tags
        self.included_local_tags = ['*'] if included_local_tags is None else included_local_tags
        self.excluded_local_tags = excluded_local_tags or []
        self.local_variables = {}
        # values specific to a local: self.local_values[local_repository.name][key] = value
        # used to override remote parameters

    def format_value(self, value, local_repository, use_constant_values=False):
        if value is None:
            return None
        assert isinstance(local_repository, LocalRepository)
        variables = {}
        variables.update(self.variables)
        variables.update(local_repository.variables)
        if local_repository.name in self.local_variables:
            variables.update(self.local_variables[local_repository.name])
        if use_constant_values:
            variables.update(self.constant_format_values)
        try:
            formatted_value = value % variables
        except KeyError as e:
            txt = text_type(e)[len('KeyError:'):]
            raise ValueError('Unable to format \'%s\': variable %s is missing' % (value, txt))
        return formatted_value

    def backup(self, local_repository, force=False):
        """ perform the backup and log all errors
        """
        logger.info('remote backup %s of local repository %s' % (self.name, local_repository.name))
        info = self.get_info(local_repository)
        assert isinstance(info, RepositoryInfo)
        assert isinstance(local_repository, LocalRepository)
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
        # collect only (but all) variables that are related to host and time
        info.variables = {k: v for (k, v) in local_repository.variables if k in self.constant_format_values}
        # these variables are required for a valid restore
        try:
            if self.can_execute_command(''):
                lock_ = local_repository.get_lock()
            export_data_path = self.apply_backup_filters(local_repository)
            self.do_backup(local_repository, export_data_path)
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
                    local_repository.release_lock(lock_)
            except Exception as e:
                cprint('unable to release lock. %s' % text_type(e), RED)
        if self.can_execute_command('# register this remote state'):
            self.set_info(local_repository, info)
        return info.last_state_valid

    def do_backup(self, local_repository, export_data_path):
        raise NotImplementedError

    def apply_backup_filters(self, local_repository):
        assert isinstance(local_repository, LocalRepository)
        next_path = local_repository.export_data_path
        for filter_ in self.filters:
            assert isinstance(filter_, FileFilter)
            next_path = filter_.backup(next_path, self.filter_private_path(local_repository, filter_),
                                       allow_in_place=False)
        return next_path

    def apply_restore_filters(self, local_repository):
        assert isinstance(local_repository, LocalRepository)
        next_path = local_repository.export_data_path
        filter_data = []
        for filter_ in self.filters:
            assert isinstance(filter_, FileFilter)
            filter_data.append((filter_, next_path))
            next_path = filter_.next_path(next_path, self.filter_private_path(local_repository, filter_),
                                          allow_in_place=False)
        for filter_, next_path in reversed(filter_data):
            assert isinstance(filter_, FileFilter)
            filter_.restore(next_path, self.filter_private_path(local_repository, filter_),
                            allow_in_place=False)

    # noinspection PyMethodMayBeStatic
    def get_info(self, local_repository, force_remote=False):
        assert isinstance(local_repository, LocalRepository)
        path = os.path.join(self.private_path(local_repository), '%s.json' % self.name)
        if os.path.isfile(path):
            with codecs.open(path, 'r', encoding='utf-8') as fd:
                content = fd.read()
            return RepositoryInfo.from_str(content)
        else:
            return RepositoryInfo()

    # noinspection PyMethodMayBeStatic
    def set_info(self, local_repository, info):
        assert isinstance(local_repository, LocalRepository)
        assert isinstance(info, RepositoryInfo)
        path = os.path.join(self.private_path(local_repository), '%s.json' % self.name)
        self.ensure_dir(path, parent=True)
        content = info.to_str()
        with codecs.open(path, 'w', encoding='utf-8') as fd:
            fd.write(content)

    def restore(self, local_repository):
        info = self.get_info(local_repository, force_remote=True)
        assert isinstance(local_repository, LocalRepository)
        assert isinstance(info, RepositoryInfo)
        local_repository.variables.update(info.variables)
        next_path = local_repository.export_data_path
        for filter_ in self.filters:
            assert isinstance(filter_, FileFilter)
            next_path = filter_.next_path(next_path, self.filter_private_path(local_repository, filter_),
                                          allow_in_place=False)
        self.do_restore(local_repository, next_path)
        self.apply_restore_filters(local_repository)

    def do_restore(self, local_repository, export_data_path):
        raise NotImplementedError

    @lru_cache()
    def private_path(self, local_repository):
        assert isinstance(local_repository, LocalRepository)
        return os.path.join(local_repository.remote_private_path(self), 'remote')

    @lru_cache()
    def filter_private_path(self, local_repository, filter_):
        assert isinstance(local_repository, LocalRepository)
        assert isinstance(filter_, FileFilter)
        return os.path.join(local_repository.remote_private_path(self), 'filter-%s' % filter_.name)


class CommonRemoteRepository(RemoteRepository):
    """A RemoteRepository with meaningful implementations pour set_info/get_info"""
    parameters = RemoteRepository.parameters + [
        Parameter('metadata_url', required=True,
                  help_str='send metadata (about the successful last backup) to this URL [**]'),
        Parameter('metadata_private_key', required=True,
                  help_str='private key associated to \'metadata_url\' [**]'),
        Parameter('metadata_ca_cert', required=True,
                  help_str='private certificate associated to \'metadata_url\' [**]'),
        Parameter('metadata_keytab', required=True,
                  help_str='keytab (for Kerberos authentication) associated to \'metadata_url\' [**]'),
        Parameter('metadata_ssh_options', required=True,
                  help_str='SSH options associated to \'metadata_url\' [**]'),
    ]

    def __init__(self, name, metadata_url=None, metadata_private_key=None, metadata_ca_cert=None,
                 metadata_keytab=None, metadata_ssh_options=None, **kwargs):
        super(CommonRemoteRepository, self).__init__(name, **kwargs)
        self.metadata_url = metadata_url
        self.metadata_private_key = metadata_private_key
        self.metadata_ca_cert = metadata_ca_cert
        self.metadata_keytab = metadata_keytab
        self.metadata_ssh_options = metadata_ssh_options

    def do_restore(self, local_repository, export_data_path):
        raise NotImplementedError

    def do_backup(self, local_repository, export_data_path):
        raise NotImplementedError

    def _get_metadata_backend(self, local_repository):
        assert isinstance(local_repository, LocalRepository)
        metadata_url = self.format_value(self.metadata_url, local_repository, use_constant_values=True)
        if metadata_url.endswith('/'):
            metadata_url += '%s.json' % local_repository.name
        metadata_private_key = self.format_value(self.metadata_private_key, local_repository, use_constant_values=True)
        metadata_ca_cert = self.format_value(self.metadata_ca_cert, local_repository, use_constant_values=True)
        metadata_keytab = self.format_value(self.metadata_keytab, local_repository, use_constant_values=True)
        metadata_ssh_options = self.format_value(self.metadata_ssh_options, local_repository, use_constant_values=True)
        backend = get_backend(self, metadata_url, keytab=metadata_keytab, private_key=metadata_private_key,
                              ca_cert=metadata_ca_cert, ssh_options=metadata_ssh_options, rsync_executable='rsync',
                              curl_executable='curl', scp_executable='scp', ssh_executable='ssh')
        assert isinstance(backend, StorageBackend)
        return backend

    @lru_cache()
    def get_info(self, local_repository, force_remote=False):
        assert isinstance(local_repository, LocalRepository)
        path = os.path.join(self.private_path(local_repository), '%s.json' % self.name)
        if not os.path.isfile(path) or force_remote:
            self.ensure_dir(path, parent=True)
            backend = self._get_metadata_backend(local_repository)
            backend.sync_file_to_local(path)
        if os.path.isfile(path) and not force_remote:
            with codecs.open(path, 'r', encoding='utf-8') as fd:
                content = fd.read()
            return RepositoryInfo.from_str(content)
        return RepositoryInfo()

    def set_info(self, local_repository, info):
        assert isinstance(local_repository, LocalRepository)
        assert isinstance(info, RepositoryInfo)
        path = os.path.join(self.private_path(local_repository), '%s.json' % self.name)
        self.ensure_dir(path, parent=True)
        content = info.to_str()
        with codecs.open(path, 'w', encoding='utf-8') as fd:
            fd.write(content)
        backend = self._get_metadata_backend(local_repository)
        backend.sync_file_from_local(path)


class GitRepository(CommonRemoteRepository):
    """Add a remote to a local repository and push local modification to this remote.
    Can use https (with password or kerberos auth) or git+ssh remotes (with private key authentication).
    local and remote branches are always named 'master'.
    """

    parameters = CommonRemoteRepository.parameters + [
        Parameter('git_executable', converter=check_executable, common=True,
                  help_str='path of the git executable (default: "git")'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication) [*]'),
        Parameter('private_key', converter=check_file,
                  help_str='absolute path of the private key file (for SSH key authentication) [*]'),
        Parameter('remote_url', help_str='URL of the remote server, including username and password (e.g.: '
                                         'git@mygitlab.example.org/project.git or '
                                         'https://username:password@mygitlab.example.org/username/project.git). '
                                         'The password is not required for SSH connections (you should use SSH keys).'
                                         'The remote repository must already exists. If you created it by hand, do not '
                                         'forget to set \'git config --bool core.bare true\'. [*]',
                  converter=check_git_url),
        Parameter('commit_email', help_str='user email used for signing commits (default: "polyarchiv@19pouces.net")'),
        Parameter('commit_name', help_str='user name used for signing commits (default: "polyarchiv")'),
        Parameter('commit_message', help_str='commit message (default: "Backup %(Y)s/%(m)s/%(d)s %(H)s:%(M)s") [*]'),
    ]

    def __init__(self, name, remote_url='', remote_branch='master', git_executable='git', private_key=None,
                 keytab=None, commit_name='polyarchiv', commit_email='polyarchiv@19pouces.net',
                 commit_message='Backup %(Y)s/%(m)s/%(d)s %(H)s:%(M)s', **kwargs):
        super(GitRepository, self).__init__(name, **kwargs)
        self.keytab = keytab
        self.private_key = private_key
        self.remote_url = remote_url
        self.remote_branch = remote_branch
        self.git_executable = git_executable
        self.commit_name = commit_name
        self.commit_email = commit_email
        self.commit_message = commit_message

    def do_backup(self, local_repository, export_data_path):
        assert isinstance(local_repository, LocalRepository)  # just to help PyCharm
        worktree = export_data_path
        git_dir = os.path.join(self.private_path(local_repository), 'git')
        git_config_path = os.path.join(git_dir, '.gitconfig')
        if not os.path.isfile(git_config_path):
            self.execute_command([self.git_executable, 'config', '--global', 'user.email', self.commit_email],
                                 env={'HOME': git_dir})
            self.execute_command([self.git_executable, 'config', '--global', 'user.name', self.commit_name],
                                 env={'HOME': git_dir})
        os.chdir(worktree)
        git_command = [self.git_executable, '--git-dir', git_dir, '--work-tree', worktree]
        self.execute_command(git_command + ['init'], cwd=worktree)
        self.execute_command(git_command + ['add', '.'])
        # noinspection PyTypeChecker
        self.execute_command(git_command + ['commit', '-am', self.format_value(self.commit_message, local_repository)],
                             ignore_errors=True, env={'HOME': self.private_path(local_repository)})

        remote_url = self.format_value(self.remote_url, local_repository)
        if not self.check_remote_url(local_repository):
            raise ValueError('Invalid remote repository: %s' % remote_url)
        cmd = []
        if self.keytab:
            cmd += ['k5start', '-q', '-f', self.format_value(self.keytab, local_repository), '-U', '--']

        cmd += git_command + ['push', remote_url, 'master:master']
        # noinspection PyTypeChecker
        if self.private_key and not remote_url.startswith('http'):
            private_key = self.format_value(self.private_key, local_repository)
            cmd = ['ssh-agent', 'bash', '-c', 'ssh-add %s ; %s' % (private_key, ' '.join(cmd))]
        self.execute_command(cmd, cwd=worktree)

    def check_remote_url(self, local_repository):
        return True

    def do_restore(self, local_repository, export_data_path):
        assert isinstance(local_repository, LocalRepository)  # just to help PyCharm
        worktree = export_data_path
        git_dir = os.path.join(self.private_path(local_repository), 'git')
        for path in (worktree, git_dir):
            if os.path.exists(path) and self.can_execute_command(['rm', '-rf', path]):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        self.execute_command([self.git_executable, 'config', '--global', 'user.email', self.commit_email],
                             env={'HOME': git_dir})
        self.execute_command([self.git_executable, 'config', '--global', 'user.name', self.commit_name],
                             env={'HOME': git_dir})
        remote_url = self.format_value(self.remote_url, local_repository)
        cmd = [self.git_executable, 'clone', '--separate-git-dir', git_dir, remote_url, worktree]
        if self.keytab:
            cmd += ['k5start', '-q', '-f', self.format_value(self.keytab, local_repository), '-U', '--']
        if self.private_key and not remote_url.startswith('http'):
            private_key = self.format_value(self.private_key, local_repository)
            cmd = ['ssh-agent', 'bash', '-c', 'ssh-add %s ; %s' % (private_key, ' '.join(cmd))]
        self.execute_command(cmd, cwd=worktree)


class GitlabRepository(GitRepository):
    """Add a remote to a local repository and push local modification to this remote.
    If the 'private_key' is set, then git+ssh is used for pushing data.
    Otherwise, use password or kerberos auth with git+http.

    The remote repository is automatically created if required using the HTTP API provided by Gitlab.
    """
    parameters = GitRepository.parameters[:-1] + [
        Parameter('gitlab_url', help_str='HTTP URL of the gitlab server (e.g.: \'https://mygitlab.example.org/\') [*]'),
        Parameter('project_name', help_str='Name of the Gitlab project (e.g. \'myuser/myproject\')[*]'),
        Parameter('username', help_str='Username to use for pushing data. If you use git+ssh, use the SSH username'
                                       ' (often \'git\'), otherwise use your real username. [*]'),
        Parameter('password', help_str='Password for HTTP auth (if private_key and keytab are not set) [*]'),
        Parameter('api_key', help_str='API key allowing for creating new repositories [*]'),
    ]

    def __init__(self, name, gitlab_url='', api_key=None, project_name='', username='', password='', private_key=None,
                 **kwargs):
        parsed = urlparse(gitlab_url)
        if private_key:
            remote_url = '%s@%s.git' % (username, parsed.hostname)
        else:
            remote_url = '%s://%s:%s@%s/%s.git' % (parsed.scheme, username, password, parsed.hostname, project_name)
        # noinspection PyTypeChecker
        super(GitlabRepository, self).__init__(name, private_key=private_key, remote_url=remote_url, **kwargs)
        self.api_key = api_key
        self.project_name = project_name
        self.api_url = '%s://%s/api/v3' % (parsed.scheme, parsed.hostname)

    def check_remote_url(self, local_repository):
        project_name = self.format_value(self.project_name, local_repository)
        api_url = self.format_value(self.api_url, local_repository)
        api_key = self.format_value(self.api_key, local_repository)
        remote_url = self.format_value(self.remote_url, local_repository)
        headers = {'PRIVATE-TOKEN': api_key}
        r = requests.get('%s/projects/%s' % (api_url, quote_plus(project_name)), headers=headers)
        if r.status_code == requests.codes.ok:
            return True
        # noinspection PyTypeChecker
        namespace, sep, name = project_name.partition('/')
        data = {'name': name, 'namespace': namespace}
        if self.can_execute_command(['curl', '-X', 'POST', '-H', 'PRIVATE-TOKEN: %s' % api_key,
                                     '%s/projects/?%s' % (api_url, urlencode(data))]):
            r = requests.post('%s/projects/' % api_url, headers=headers, params=data)
            if r.status_code > 200:
                raise ValueError('Unable to create repository %s' % remote_url)
        # GET /projects/:id/events
        return True


class Synchronize(CommonRemoteRepository):
    parameters = CommonRemoteRepository.parameters + [
        Parameter('remote_url', required=True, help_str='synchronize data to this URL. Must be a folder name [*]'),
        Parameter('private_key', required=True, help_str='private key or certificate associated to \'remote_url\' [*]'),
        Parameter('ca_cert', required=True, help_str='CA certificate associated to \'remote_url\'. '
                                                     'Set to "any" for not checking certificates [*]'),
        Parameter('keytab', required=True, help_str='keytab (for Kerberos) associated to \'remote_url\' [*]'),
        Parameter('ssh_options', required=True, help_str='SSH options associated to \'url\' [*]'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication) [*]'),
    ]

    def __init__(self, name, remote_url='', keytab=None, private_key=None, ca_cert=None, ssh_options=None, **kwargs):
        super(Synchronize, self).__init__(name, **kwargs)
        self.remote_url = remote_url
        self.keytab = keytab
        self.private_key = private_key
        self.ca_cert = ca_cert
        self.ssh_options = ssh_options

    def do_backup(self, local_repository, export_data_path):
        backend = self._get_backend(local_repository)
        backend.sync_dir_from_local(export_data_path)

    def _get_backend(self, local_repository):
        remote_url = self.format_value(self.remote_url, local_repository)
        keytab = self.format_value(self.keytab, local_repository)
        private_key = self.format_value(self.private_key, local_repository)
        ca_cert = self.format_value(self.ca_cert, local_repository)
        ssh_options = self.format_value(self.ssh_options, local_repository)
        backend = get_backend(local_repository, remote_url, keytab=keytab, private_key=private_key, ca_cert=ca_cert,
                              ssh_options=ssh_options)
        return backend

    def do_restore(self, local_repository, export_data_path):
        backend = self._get_backend(local_repository)
        backend.sync_dir_to_local(export_data_path)


class TarArchive(CommonRemoteRepository):
    """Collect all files of your local repository into a .tar archive (.tar.gz, .tar.bz2 or .tar.xz) and copy it
    to a remote server with 'cURL'. If the remote URL begins by 'file://', then the 'cp' command is used instead.

    """

    excluded_files = {'.git', '.gitignore'}
    parameters = CommonRemoteRepository.parameters + [
        Parameter('remote_url', required=True, help_str='synchronize data to this URL. Must end by ".tar.gz", '
                                                        '"tar.bz2", "tar.xz" [*]'),
        Parameter('private_key', required=True, help_str='private key or certificate associated to \'remote_url\' [*]'),
        Parameter('ca_cert', required=True, help_str='CA certificate associated to \'remote_url\'. '
                                                     'Set to "any" for not checking certificates [*]'),
        Parameter('keytab', required=True, help_str='keytab (for Kerberos) associated to \'remote_url\' [*]'),
        Parameter('ssh_options', required=True, help_str='SSH options associated to \'url\' [*]'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication) [*]'),
        Parameter('tar_executable', converter=check_executable, common=True,
                  help_str='path of the rsync executable (default: "tar")'),
        Parameter('curl_executable', converter=check_executable, common=True,
                  help_str='path of the rsync executable (default: "curl")'),
    ]

    def __init__(self, name, tar_executable='tar', curl_executable='curl', remote_url='', keytab=None, private_key=None,
                 ca_cert=None, ssh_options=None, **kwargs):
        super(TarArchive, self).__init__(name, **kwargs)
        self.tar_executable = tar_executable
        self.curl_executable = curl_executable
        self.remote_url = remote_url
        self.keytab = keytab
        self.private_key = private_key
        self.ca_cert = ca_cert
        self.ssh_options = ssh_options

    def _get_backend(self, local_repository):
        remote_url = self.format_value(self.remote_url, local_repository)
        keytab = self.format_value(self.keytab, local_repository)
        private_key = self.format_value(self.private_key, local_repository)
        ca_cert = self.format_value(self.ca_cert, local_repository)
        ssh_options = self.format_value(self.ssh_options, local_repository)
        backend = get_backend(local_repository, remote_url, keytab=keytab, private_key=private_key, ca_cert=ca_cert,
                              ssh_options=ssh_options)
        return backend

    def do_backup(self, local_repository, export_data_path):
        assert isinstance(local_repository, LocalRepository)
        backend = self._get_backend(local_repository)
        remote_url = self.format_value(self.remote_url, local_repository)
        archive_filename = os.path.join(self.private_path(local_repository), 'archive')
        if remote_url.endswith('tar.gz'):
            archive_filename += '.tar.gz'
            cmd = [self.tar_executable, '-czf', archive_filename]
        elif remote_url.endswith('tar.bz2'):
            archive_filename += '.tar.bz2'
            cmd = [self.tar_executable, '-cjf', archive_filename]
        elif remote_url.endswith('tar.xz'):
            archive_filename += '.tar.xz'
            cmd = [self.tar_executable, '-cJf', archive_filename]
        else:
            raise ValueError('invalid tar format: %s' % remote_url)
        filenames = os.listdir(export_data_path)
        filenames.sort()
        cmd += filenames
        returncode, stdout, stderr = self.execute_command(cmd, cwd=export_data_path, ignore_errors=True)
        error = None
        if returncode != 0:
            error = ValueError('unable to create archive %s' % archive_filename)
        else:
            try:
                backend.sync_file_from_local(archive_filename)
            except Exception as e:
                error = e
        if os.path.isfile(archive_filename) and self.can_execute_command(['rm', archive_filename]):
            os.remove(archive_filename)
        if error is not None:
            raise error

    def do_restore(self, local_repository, export_data_path):
        assert isinstance(local_repository, LocalRepository)
        backend = self._get_backend(local_repository)
        remote_url = self.format_value(self.remote_url, local_repository)
        archive_filename = os.path.join(self.private_path(local_repository), 'archive')
        if remote_url.endswith('tar.gz'):
            archive_filename += '.tar.gz'
        elif remote_url.endswith('tar.bz2'):
            archive_filename += '.tar.bz2'
        elif remote_url.endswith('tar.xz'):
            archive_filename += '.tar.xz'
        else:
            raise ValueError('invalid tar format: %s' % remote_url)
        backend.sync_file_to_local(archive_filename)
        self.execute_command([self.tar_executable, '-xf', archive_filename], cwd=export_data_path)


class SmartTarArchive(CommonRemoteRepository):
    """Collect all files of your local repository into a .tar archive (.tar.gz, .tar.bz2 or .tar.xz) and copy it
    to a remote server with 'cURL'. If the remote URL begins by 'file://', then the 'cp' command is used instead.

    """

    excluded_files = {'.git', '.gitignore'}
    parameters = CommonRemoteRepository.parameters + [
        Parameter('remote_url', required=True, help_str='synchronize data to this URL. Must end by ".tar.gz", '
                                                        '"tar.bz2", "tar.xz" [*]'),
        Parameter('private_key', required=True, help_str='private key or certificate associated to \'remote_url\' [*]'),
        Parameter('ca_cert', required=True, help_str='CA certificate associated to \'remote_url\'. '
                                                     'Set to "any" for not checking certificates [*]'),
        Parameter('keytab', required=True, help_str='keytab (for Kerberos) associated to \'remote_url\' [*]'),
        Parameter('ssh_options', required=True, help_str='SSH options associated to \'url\' [*]'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication) [*]'),
        Parameter('tar_executable', converter=check_executable, common=True,
                  help_str='path of the rsync executable (default: "tar")'),
        Parameter('curl_executable', converter=check_executable, common=True,
                  help_str='path of the rsync executable (default: "curl")'),
    ]

    def __init__(self, name, tar_executable='tar', curl_executable='curl', remote_url='', keytab=None, private_key=None,
                 ca_cert=None, ssh_options=None, **kwargs):
        super(SmartTarArchive, self).__init__(name, **kwargs)
        self.tar_executable = tar_executable
        self.curl_executable = curl_executable
        self.remote_url = remote_url
        self.keytab = keytab
        self.private_key = private_key
        self.ca_cert = ca_cert
        self.ssh_options = ssh_options

    def _get_backend(self, local_repository):
        remote_url = self.format_value(self.remote_url, local_repository)
        keytab = self.format_value(self.keytab, local_repository)
        private_key = self.format_value(self.private_key, local_repository)
        ca_cert = self.format_value(self.ca_cert, local_repository)
        ssh_options = self.format_value(self.ssh_options, local_repository)
        backend = get_backend(local_repository, remote_url, keytab=keytab, private_key=private_key, ca_cert=ca_cert,
                              ssh_options=ssh_options)
        return backend

    def do_backup(self, local_repository, export_data_path):
        assert isinstance(local_repository, LocalRepository)
        backend = self._get_backend(local_repository)
        remote_url = self.format_value(self.remote_url, local_repository)
        archive_filename = os.path.join(self.private_path(local_repository), 'archive')
        if remote_url.endswith('tar.gz'):
            archive_filename += '.tar.gz'
            cmd = [self.tar_executable, '-czf', archive_filename]
        elif remote_url.endswith('tar.bz2'):
            archive_filename += '.tar.bz2'
            cmd = [self.tar_executable, '-cjf', archive_filename]
        elif remote_url.endswith('tar.xz'):
            archive_filename += '.tar.xz'
            cmd = [self.tar_executable, '-cJf', archive_filename]
        else:
            raise ValueError('invalid tar format: %s' % remote_url)
        filenames = os.listdir(export_data_path)
        filenames.sort()
        cmd += filenames
        returncode, stdout, stderr = self.execute_command(cmd, cwd=export_data_path, ignore_errors=True)
        error = None
        if returncode != 0:
            error = ValueError('unable to create archive %s' % archive_filename)
        else:
            try:
                backend.sync_file_from_local(archive_filename)
            except Exception as e:
                error = e
        if os.path.isfile(archive_filename) and self.can_execute_command(['rm', archive_filename]):
            os.remove(archive_filename)
        if error is not None:
            raise error

    def do_restore(self, local_repository, export_data_path):
        assert isinstance(local_repository, LocalRepository)
        backend = self._get_backend(local_repository)
        remote_url = self.format_value(self.remote_url, local_repository)
        archive_filename = os.path.join(self.private_path(local_repository), 'archive')
        if remote_url.endswith('tar.gz'):
            archive_filename += '.tar.gz'
        elif remote_url.endswith('tar.bz2'):
            archive_filename += '.tar.bz2'
        elif remote_url.endswith('tar.xz'):
            archive_filename += '.tar.xz'
        else:
            raise ValueError('invalid tar format: %s' % remote_url)
        backend.sync_file_to_local(archive_filename)
        self.execute_command([self.tar_executable, '-xf', archive_filename], cwd=export_data_path)
