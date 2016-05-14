# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import datetime
import logging

from polyarchiv.termcolor import YELLOW, RED
from polyarchiv.termcolor import cprint

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urlparse import urlparse
import os

from polyarchiv.conf import Parameter, strip_split, check_executable, check_file, CheckOption, bool_setting
from polyarchiv.locals import GitRepository as LocalGitRepository, LocalRepository, FileRepository
from polyarchiv.repository import Repository, RepositoryInfo
from polyarchiv.utils import text_type, ensure_dir

__author__ = 'mgallet'
logger = logging.getLogger('polyarchiv.remotes')


class RemoteRepository(Repository):
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

    def format_value(self, value, local_repository):
        assert isinstance(local_repository, LocalRepository)
        variables = {'name': local_repository.name}
        variables.update(local_repository.variables)
        if local_repository.name in self.local_variables:
            variables.update(self.local_variables[local_repository.name])
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
            if self.can_execute_command(''):
                lock_ = local_repository.get_lock()
            self.do_backup(local_repository)
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

    def do_backup(self, local_repository):
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

    def get_last_backup_date(self, local_repository):
        raise NotImplementedError

    def restore(self, local_repository):
        raise NotImplementedError


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
    """Add a remote to a local repository and push local modification to this remote.
    Can use https (password or kerberos auth) or git+ssh remotes (with private key authentication).
    """
    parameters = RemoteRepository.parameters + [
        Parameter('git_executable', converter=check_executable, help_str='path of the git executable (default: "git")'),
        Parameter('remote_url', help_str='URL of the remote server, include username and password (e.g.: '
                                         'git@mygitlab.example.org:username/project.git,'
                                         'https://username:password@mygitlab.example.org/username/project.git) [*]'),
        Parameter('remote_branch', help_str='name of the remote branch [*]'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication) [*]'),
        Parameter('private_key', converter=check_file,
                  help_str='absolute path of the private key file (for SSH key authentication) [*]'),
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
        assert isinstance(local_repository, LocalGitRepository)  # just to help PyCharm
        cmd = []
        if self.keytab:
            cmd += ['k5start', '-q', '-f', self.format_value(self.keytab, local_repository), '-U', '--']
        remote_url = self.format_value(self.remote_url, local_repository)
        remote_branch = self.format_value(self.remote_branch, local_repository)
        cmd += [self.git_executable, 'push', remote_url, '+master:%s' % remote_branch]
        # noinspection PyTypeChecker
        private_key = self.private_key
        if private_key and not remote_url.startswith('http'):
            private_key = self.format_value(private_key, local_repository)
            cmd = ['ssh-agent', 'bash', '-c', 'ssh-add %s ; %s' % (private_key, ' '.join(cmd))]
        self.execute_command(cmd, cwd=local_repository.local_path)

    def get_last_backup_date(self, local_repository):
        # git archive --remote=git://git.foo.com/project.git HEAD:path /to/directory filename | tar -x
        pass


class Rsync(RemoteRepository):
    """Send local files to the remote repository using 'rsync'. """
    parameters = RemoteRepository.parameters + [
        Parameter('rsync_executable', converter=check_executable,
                  help_str='path of the rsync executable (default: "rsync")'),
        Parameter('remote_url', help_str='remote server and path (e.g. login:password@server:/foo/bar/ [*]'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication) [*]'),
        Parameter('private_key', converter=check_file,
                  help_str='absolute path of the private key file (for SSH key authentication) [*]'),
    ]

    def __init__(self, name, rsync_executable='rsync', remote_url='', keytab=None, private_key=None, **kwargs):
        super(Rsync, self).__init__(name, **kwargs)
        self.rsync_executable = rsync_executable
        self.remote_url = remote_url
        self.keytab = keytab
        self.private_key = private_key

    def do_backup(self, local_repository):
        assert isinstance(local_repository, FileRepository)
        cmd = []
        if self.keytab:
            cmd += ['k5start', '-q', '-f', self.format_value(self.keytab, local_repository), '-U', '--']
        cmd += [self.rsync_executable, '-az', '--delete', '--exclude=%s' % local_repository.PRIVATE_FOLDER, '-S']
        local_path = local_repository.local_path
        if not local_path.endswith(os.path.sep):
            local_path += os.path.sep
        remote_url = self.format_value(self.remote_url, local_repository)
        if not remote_url.endswith(os.path.sep):
            remote_url += os.path.sep
        private_key = self.private_key
        if private_key:
            private_key = self.format_value(private_key, local_repository)
            cmd += ['-e', 'ssh -i %s' % private_key]
        else:
            cmd += ['-e', 'ssh']
        cmd += [local_path, remote_url]
        self.execute_command(cmd, cwd=local_repository.local_path)


def check_curl_url(remote_url):
    """Check if the given URL starts by a valid scheme

    >>> check_curl_url("scp://localhost/tmp") == 'scp://localhost/tmp'
    True

    """
    parsed_url = urlparse(remote_url)
    if parsed_url.scheme not in ('http', 'https', 'scp', 'ftp', 'ftps', 'sftp', 'smb', 'smbs', 'file'):
        raise ValueError('Invalid scheme for remote URL: %s' % parsed_url.scheme)
    return remote_url


class TarArchive(RemoteRepository):
    """Collect all files of your local repository into a .tar archive (.tar.gz, .tar.bz2 or .tar.xz) and copy it
    to a remote server with 'cURL'. If the remote URL begins by 'file://', then the 'cp' command is used instead.

    """
    excluded_files = {'.git', '.gitignore'}
    parameters = RemoteRepository.parameters + [
        Parameter('remote_url', converter=check_curl_url,
                  help_str='destination URL (e.g.: \'ftp://example.org/path/\' or '
                           '\'https://example.org/path\'). \'file://\' URLs are handled by a \'cp\' command, other ones'
                           ' are handled by \'curl\' command. Most of protocols known by cURL can be used:'
                           ' ftp(s), http(s) with WebDAV, scp, sftp, smb, smbs. You can specify user and password'
                           ' in URL: \'scheme://user:password@host/path\' [*]'),
        Parameter('user', help_str='username (if not set in the URL) [*]'),
        Parameter('password', help_str='password (if not set in the URL) [*]'),
        Parameter('archive_prefix', help_str='prefix of the archive names (default: "archive") [*]'),
        Parameter('proxy',
                  help_str='use this proxy for connections (e.g. username:password@proxy.example.org:8080) [*]'),
        Parameter('insecure', converter=bool_setting, help_str='true|false: do not check certificates'),
        Parameter('cert', converter=check_file,
                  help_str='[HTTPS|FTPS backend] certificate to provide to the server [*]'),
        Parameter('cacert', converter=check_file, help_str='[HTTPS|FTPS backend] CA certificate authenticating'
                                                           ' the server [*]'),
        Parameter('date_format', help_str='date format for the generated archives (default: "%Y-%m-%d_%H-%M")'),
        Parameter('keytab', converter=check_file,
                  help_str='absolute path of the keytab file (for Kerberos authentication) [*]'),
        Parameter('private_key', converter=check_file,
                  help_str='[HTTPS|FTPS|SSH backend] absolute path of the private key file [*]'),
        Parameter('tar_format', converter=CheckOption(['tar.gz', 'tar.bz2', 'tar.xz']),
                  help_str='one of "tar.gz", "tar.bz2" (default), "tar.xz"'),
        Parameter('tar_executable', converter=check_executable,
                  help_str='path of the rsync executable (default: "tar")'),
        Parameter('curl_executable', converter=check_executable,
                  help_str='path of the rsync executable (default: "curl")'),
    ]

    def __init__(self, name, tar_executable='tar', curl_executable='curl', remote_url='', user='', password='',
                 insecure=False, cacert=None, cert=None, archive_prefix='archive',
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
        self.cert = cert

    def do_backup(self, local_repository):
        assert isinstance(local_repository, FileRepository)
        error = None
        excluded_files = self.excluded_files | {local_repository.PRIVATE_FOLDER}
        filenames = {x for x in os.listdir(local_repository.local_path)} - excluded_files
        filenames = [x for x in filenames]
        filenames.sort()
        # noinspection PyTypeChecker
        now_str = datetime.datetime.now().strftime(self.date_format)
        prefix = self.format_value(self.archive_prefix, local_repository)
        archive_filename = os.path.join(local_repository.local_path,
                                        '%s-%s.%s' % (prefix, now_str, self.tar_format))
        if self.tar_format == 'tar.gz':
            cmd = [self.tar_executable, '-czf']
        elif self.tar_format == 'tar.bz2':
            cmd = [self.tar_executable, '-cjf']
        elif self.tar_format == 'tar.xz':
            cmd = [self.tar_executable, '-cJf']
        else:
            raise ValueError('invalid tar format: %s' % self.tar_format)
        cmd.append(archive_filename)
        cmd += filenames
        returncode = self.execute_command(cmd, cwd=local_repository.local_path, ignore_errors=True)
        if returncode != 0:
            error = ValueError('unable to create archive %s' % archive_filename)
        else:
            cmd = []
            if self.keytab:
                cmd += ['k5start', '-q', '-f', self.format_value(self.keytab, local_repository), '-U', '--']
            remote_url = self.format_value(self.remote_url, local_repository)
            # noinspection PyTypeChecker
            if not remote_url.endswith('/'):
                remote_url += '/'
            # noinspection PyTypeChecker
            if remote_url.startswith('file://'):
                ensure_dir(remote_url[7:], parent=False)
                cmd += ['cp', archive_filename, remote_url[7:]]
            else:

                cmd += [self.curl_executable, '--anyauth']
                if self.insecure:
                    cmd += ['-k']
                if self.cacert:
                    cmd += ['--cacert', self.format_value(self.cacert, local_repository)]
                if self.cert:
                    cmd += ['--cert', self.format_value(self.cert, local_repository)]
                parsed_url = urlparse(remote_url)
                if not parsed_url.username and not parsed_url.password and self.user and self.password:
                    cmd += ['-u', '%s:%s' % (self.format_value(self.user, local_repository),
                                             self.format_value(self.password, local_repository))]
                if self.private_key:
                    cmd += ['--key', self.format_value(self.private_key, local_repository)]
                if self.proxy:
                    cmd += ['-x', self.format_value(self.proxy, local_repository), '--proxy-anyauth']
                cmd += ['-T', archive_filename]
                # noinspection PyTypeChecker
                if remote_url.startswith('ftps'):
                    cmd += ['--ftp-ssl', 'ftp' + remote_url[4:]]
                else:
                    cmd += [remote_url]
            returncode = self.execute_command(cmd)
            if returncode != 0:
                error = ValueError('unable to create archive %s' % archive_filename)
        if os.path.isfile(archive_filename) and self.can_execute_command(['rm', archive_filename]):
            os.remove(archive_filename)
        if error is not None:
            raise error


class Duplicity(RemoteRepository):
    """Send local files to the remote repository using the 'duplicity' tool. """
    parameters = RemoteRepository.parameters + [
        Parameter('remote_url',
                  help_str='destination URL with the username (e.g.: ftp://user:password@example.org/path/,'
                           'https://user:password@example.org/path). Please check Duplicity\'s documentation.'
                           'Password can be separately set with the \'password\' option. [*]'),
        Parameter('encrypt_key_id', help_str='[GPG] encrypt with this public key instead of symmetric encryption. [*]'),
        Parameter('sign_key_id', help_str='[GPG] All backup files will be signed with keyid key. [*]'),
        Parameter('encrypt_passphrase', help_str='[GPG] This passphrase is passed to GnuPG. [*]'),
        Parameter('sign_passphrase', help_str='[GPG] This passphrase is passed to GnuPG for the sign_key. [*]'),
        Parameter('no_encryption', converter=bool_setting, help_str='true|false: do not use GnuPG to encrypt '
                                                                    'remote files.'),
        Parameter('private_key', converter=check_file, help_str='[SSH backend] The private SSH key (filename) [*]'),
        Parameter('password', help_str='upload password [*]'),

        Parameter('full_if_older_than',
                  help_str='Perform a full backup if an incremental backup is requested, but the latest full backup in '
                           'the collection is older than the given time.'),
        Parameter('max_block_size', help_str='determines the number of the blocks examined for changes during the '
                                             'diff process.'),
        Parameter('no_compression', converter=bool_setting, help_str='true|false: do not use GZip to compress remote '
                                                                     'files.'),
        Parameter('volsize', help_str='Change the volume size to number Mb. Default is 25Mb.'),
        Parameter('always_full', converter=bool_setting,
                  help_str='true|false: perform a full backup. A new backup chain is started even if signatures are '
                           'available for an incremental backup.'),
        Parameter('always_verify', converter=bool_setting,
                  help_str='true|false: always perform a verify check after a backup: restore backup contents '
                           'temporarily file by file and compare against the local path\'s contents. Can take a lot of '
                           'time!'),

        Parameter('gpg_encrypt_secret_keyring',
                  help_str='[GPG] This option can only be used with encrypt_key, and changes the path to the secret '
                           'keyring for the encrypt key to filename. Default to \'~/.gnupg/secring.gpg\' [*]'),
        Parameter('gpg_options', converter=check_executable,
                  help_str='[GPG] Allows you to pass options to gpg encryption.  The options list should be of the '
                           'form "--opt1 --opt2=parm"'),
        Parameter('rsync_options', help_str='[RSYNC backend] Options for rsync. The options list should be of the '
                                            'form "opt1=parm1 opt2=parm2"'),
        Parameter('ssh_options',
                  help_str='[SSH backend] Options for SSH. The options list should be of '
                           'the form "-oOpt1=\'parm1\' -oOpt2=\'parm2\'".'),
        Parameter('cacert', converter=check_file, help_str='[HTTPS backend] certificate to use to verify the server [*]'),
        Parameter('insecure', converter=bool_setting,
                  help_str='[HTTPS backend] true|false: do not check certificate for SSL connections'),
        Parameter('duplicity_executable', converter=check_executable,
                  help_str='path of the duplicity executable (default: \'duplicity\')'),
        Parameter('gpg_executable', converter=check_executable,
                  help_str='path of the gpg executable (default: \'gpg\')'),
    ]

    def __init__(self, name, remote_url='', encrypt_key_id=None, sign_key_id=None, encrypt_passphrase=None,
                 sign_passphrase=None, no_encryption=False, private_key=None, password=None,
                 full_if_older_than=None, max_block_size=None, no_compression=False, volsize=None,
                 always_full=False, always_verify=False, gpg_encrypt_secret_keyring=None, gpg_options=None,
                 rsync_options=None, ssh_options=None, cacert=None, insecure=False,
                 duplicity_executable='duplicity', gpg_executable=None, **kwargs):
        super(Duplicity, self).__init__(name, **kwargs)
        self.remote_url = remote_url
        self.encrypt_key_id = encrypt_key_id
        self.sign_key_id = sign_key_id
        self.encrypt_passphrase = encrypt_passphrase
        self.sign_passphrase = sign_passphrase
        self.no_encryption = no_encryption
        self.private_key = private_key
        self.password = password
        self.full_if_older_than = full_if_older_than
        self.max_block_size = max_block_size
        self.no_compression = no_compression
        self.volsize = volsize
        self.always_full = always_full
        self.always_verify = always_verify
        self.gpg_encrypt_secret_keyring = gpg_encrypt_secret_keyring
        self.gpg_options = gpg_options
        self.rsync_options = rsync_options
        self.ssh_options = ssh_options
        self.cacert = cacert
        self.insecure = insecure
        self.duplicity_executable = duplicity_executable
        self.gpg_executable = gpg_executable

    def do_backup(self, local_repository):
        assert isinstance(local_repository, FileRepository)
        cmd = []
        env = {}
        cmd += [self.duplicity_executable, '--exclude=%s' % local_repository.PRIVATE_FOLDER, ]
        local_path = local_repository.local_path
        if not local_path.endswith(os.path.sep):
            local_path += os.path.sep
        remote_url = self.format_value(self.remote_url, local_repository)
        if not remote_url.endswith(os.path.sep):
            remote_url += os.path.sep
        if self.encrypt_key_id:
            cmd += ['--encrypt-key', self.format_value(self.encrypt_key_id, local_repository)]
        if self.sign_key_id:
            cmd += ['--sign-key', self.format_value(self.sign_key_id, local_repository)]
        if self.encrypt_passphrase:
            env['PASSPHRASE'] = self.format_value(self.encrypt_passphrase, local_repository)
        if self.sign_passphrase:
            env['SIGN_PASSPHRASE'] = self.format_value(self.sign_passphrase, local_repository)
        if self.no_encryption:
            cmd += ['--no-encryption']
        if self.ssh_options and self.private_key:
            private_key = self.format_value(self.private_key, local_repository)
            cmd += ['--ssh-options', '%s -oIdentityFile=%s' % (self.ssh_options, private_key)]
        elif self.private_key:
            private_key = self.format_value(self.private_key, local_repository)
            cmd += ['--ssh-options', '-oIdentityFile=%s' % private_key]
        elif self.ssh_options:
            cmd += ['--ssh-options', self.ssh_options]
        if self.password:
            env['FTP_PASSWORD'] = self.format_value(self.password, local_repository)
        if self.full_if_older_than:
            cmd += ['--full-if-older-than', self.full_if_older_than]
        if self.max_block_size:
            cmd += ['--max-blocksize', self.max_block_size]
        if self.no_compression:
            cmd += ['--no-compression']
        if self.volsize:
            cmd += ['--volsize', self.volsize]
        if self.gpg_encrypt_secret_keyring:
            keyring = self.format_value(self.gpg_encrypt_secret_keyring, local_repository)
            cmd += ['--encrypt-secret-keyring filename', keyring]
        if self.gpg_options:
            cmd += ['--gpg-options', self.gpg_options]
        if self.rsync_options:
            cmd += ['--rsync-options', self.rsync_options]
        if self.cacert:
            cmd += ['--ssl-cacert-file', self.format_value(self.cacert, local_repository)]
        if self.insecure:
            cmd += ['--ssl-no-check-certificate']
        if self.gpg_executable:
            cmd += ['--gpg-binary', self.gpg_executable]

        for i in (0, 1):
            # only required for the optional 'verify' pass
            cmd_args = [x for x in cmd]
            if i == 0 and self.always_full:
                cmd_args += ['full']
            elif i == 1 and not self.always_verify:
                continue
            elif i == 1:
                cmd_args += ['verify']
            cmd_args += [local_path, remote_url]
            if self.command_display:
                for k, v in env.items():
                    cprint('%s=%s' % (k, v), YELLOW)
            self.execute_command(cmd_args, cwd=local_repository.local_path, env=env)
