# -*- coding=utf-8 -*-
"""Base backup sources.

  * MySQL
  * PostgreSQL
  * SQlite
  * raw files

"""
from __future__ import unicode_literals

import io
import os
import re
import subprocess

import pwd

import grp

# noinspection PyProtectedMember
from polyarchiv._vendor.ldif3 import LDIFParser
from polyarchiv.conf import Parameter, bool_setting, check_directory, check_executable, check_username
from polyarchiv.locals import LocalRepository
from polyarchiv.repository import ParameterizedObject
from polyarchiv.termcolor import YELLOW
from polyarchiv.termcolor import cprint

__author__ = 'Matthieu Gallet'


class Source(ParameterizedObject):
    """base source class"""
    parameters = ParameterizedObject.parameters + []

    def __init__(self, name, local_repository, **kwargs):
        super(Source, self).__init__(name, **kwargs)
        assert isinstance(local_repository, LocalRepository)
        self.local_repository = local_repository

    def backup(self):
        """Backup data corresponding to this source"""
        raise NotImplementedError

    def restore(self):
        """Restore data from the local backup """
        raise NotImplementedError


class RSync(Source):
    """copy all files from the given source_path to the local repository using rsync.
    The destination is a folder inside the local repository.
    """
    parameters = Source.parameters + [
        Parameter('source_path', converter=check_directory, help_str='original folder to backup', required=True),
        Parameter('destination_path', help_str='destination folder (relative path, e.g. "./files")', required=True),
        Parameter('rsync_executable', converter=check_executable, help_str='rsync executable (default: rsync)'),
        Parameter('exclude', help_str='exclude files matching PATTERN (see --exclude option from rsync). '
                                      'If PATTERN startswith @, then it should be the absolute path of a file '
                                      '(see --exclude-from option from rsync)'),
        Parameter('include', help_str='only include files matching PATTERN (see --include option from rsync). '
                                      'If PATTERN startswith @, then it should be the absolute path of a file '
                                      '(see --include-from option from rsync)'),
        Parameter('preserve_hard_links', converter=bool_setting, help_str='true|false: preserve hard links'),
    ]

    def __init__(self, name, local_repository, source_path='', destination_path='', rsync_executable='rsync',
                 exclude='', include='', preserve_hard_links='', **kwargs):
        """
        :param local_repository: local repository where files are stored
        :param source_path: absolute path of a directory to backup
        :param destination_path: relative path of the backup destination (must be a directory name, e.g. "data")
        :param rsync_executable: path of the rsync executable
        :param exclude: exclude files matching PATTERN. If PATTERN starts with '@', it must be the absolute path of
            a file (cf. the --exclude-from option from rsync)
        :param include: don't exclude files matching PATTERN. If PATTERN starts with '@', it must be the absolute path
            of a file (cf. the --include-from option from rsync)
        :param preserve_hard_links: preserve hard links
        """
        super(RSync, self).__init__(name, local_repository, **kwargs)
        self.source_path = source_path
        self.destination_path = destination_path
        self.rsync_executable = rsync_executable
        self.exclude = exclude
        self.include = include
        self.preserve_hard_links = preserve_hard_links.lower().strip() in ('yes', 'true', 'on', '1')

    def backup(self):
        cmd = [self.rsync_executable, '-a', '--delete', '-S', ]
        if self.preserve_hard_links:
            cmd.append('-H')
        # noinspection PyTypeChecker
        if self.exclude and self.exclude.startswith('@'):
            cmd += ['--exclude-from', self.exclude[1:]]
        elif self.exclude:
            cmd += ['--exclude', self.exclude]
        # noinspection PyTypeChecker
        if self.include and self.include.startswith('@'):
            cmd += ['--include-from', self.include[1:]]
        elif self.include:
            cmd += ['--include', self.include]
        dirname = os.path.join(self.local_repository.import_data_path, self.destination_path)
        self.ensure_dir(dirname)
        source = self.source_path
        if not source.endswith(os.path.sep):
            source += os.path.sep
        if not dirname.endswith(os.path.sep):
            dirname += os.path.sep
        cmd += [source, dirname]
        self.execute_command(cmd)

    def restore(self):
        cmd = [self.rsync_executable, '-a', '--delete', '-S', ]
        if self.preserve_hard_links:
            cmd.append('-H')
        dirname = os.path.join(self.local_repository.import_data_path, self.destination_path)
        self.ensure_dir(dirname)
        source = self.source_path
        if not source.endswith(os.path.sep):
            source += os.path.sep
        if not dirname.endswith(os.path.sep):
            dirname += os.path.sep
        cmd += [dirname, source]
        self.execute_command(cmd)


class MySQL(Source):
    """Dump the content of a MySQL database with the mysqldump utility to a filename in the local repository"""
    parameters = Source.parameters + [
        Parameter('host', help_str='database host'),
        Parameter('port', converter=int, help_str='database port'),
        Parameter('sudo_user', help_str='sudo user, used for all SQL operations', converter=check_username),
        Parameter('user', help_str='database user'),
        Parameter('password', help_str='database password'),
        Parameter('database', help_str='name of the backuped database', required=True),
        Parameter('destination_path', help_str='relative path of the backup destination (e.g. "database.sql")'),
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the mysqldump executable (default: "mysqldump")'),
        Parameter('restore_executable', converter=check_executable,
                  help_str='path of the mysql executable (default: "mysql")'),
    ]

    def __init__(self, name, local_repository, host='localhost', port='3306', user='', password='', database='',
                 destination_path='mysql_dump.sql', sudo_user=None, dump_executable='mysqldump',
                 restore_executable='mysql', **kwargs):
        super(MySQL, self).__init__(name, local_repository, **kwargs)
        self.sudo_user = sudo_user
        self.restore_executable = restore_executable
        self.dump_executable = dump_executable
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.destination_path = destination_path

    def backup(self):
        filename = os.path.join(self.local_repository.import_data_path, self.destination_path)
        self.ensure_dir(filename, parent=True)
        cmd = self.get_dump_cmd_list()
        if self.sudo_user:
            cmd = ['sudo', '-u', self.sudo_user] + cmd
        env = os.environ.copy()
        env.update(self.get_env())
        if self.command_display:
            for k, v in self.get_env().items():
                cprint('%s=%s' % (k, v), YELLOW)
        if not self.can_execute_command(cmd + ['>', filename]):
            filename = os.devnull  # run the dump even in dry mode
        with open(filename, 'wb') as fd:
            p = subprocess.Popen(cmd, env=env, stdout=fd, stderr=self.stderr)
            p.communicate()
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, cmd[0])

    def restore(self):
        filename = os.path.join(self.local_repository.import_data_path, self.destination_path)
        if not os.path.isfile(filename):
            return
        cmd = self.get_restore_cmd_list()
        if self.sudo_user:
            cmd = ['sudo', '-u', self.sudo_user] + cmd
        env = os.environ.copy()
        env.update(self.get_env())
        if self.command_display:
            for k, v in self.get_env().items():
                cprint('%s=%s' % (k, v), YELLOW)
        # noinspection PyTypeChecker
        with open(filename, 'rb') as fd:
            self.execute_command(cmd, env=env, stdin=fd, stderr=self.stderr, stdout=self.stdout)

    def get_dump_cmd_list(self):
        """ :return:
        :rtype: :class:`list` of :class:`str`
        """
        command = [self.dump_executable]
        if self.user:
            command += ['--user=%s' % self.user]
        if self.password:
            command += ['--password=%s' % self.password]
        if self.host:
            command += ['--host=%s' % self.host]
        if self.port:
            command += ['--port=%s' % self.port]
        command += [self.database]
        return command

    def get_restore_cmd_list(self):
        """ :return:
        :rtype: :class:`list` of :class:`str`
        """
        command = self.get_dump_cmd_list()
        command[0] = self.restore_executable
        return command

    def get_env(self):
        """Extra environment variables to be passed to shell execution"""
        return {}


class PostgresSQL(MySQL):
    """Dump the content of a PostgresSQL database with the pg_dump utility to a filename in the local repository"""
    parameters = MySQL.parameters[:-2] + [
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the pg_dump executable (default: "pg_dump")'),
        Parameter('restore_executable', converter=check_executable,
                  help_str='path of the psql executable (default: "psql")'),
    ]

    def __init__(self, name, local_repository, port='5432', dump_executable='pg_dump', restore_executable='psql',
                 **kwargs):
        super(PostgresSQL, self).__init__(name, local_repository, port=port, dump_executable=dump_executable,
                                          restore_executable=restore_executable, **kwargs)

    def get_dump_cmd_list(self):
        command = [self.dump_executable]
        if self.user:
            command += ['--username=%s' % self.user]
        if self.host:
            command += ['--host=%s' % self.host]
        if self.port:
            command += ['--port=%s' % self.port]
        command += [self.database]
        return command

    def get_env(self):
        """Extra environment variables to be passed to shell execution"""
        if self.password:
            return {'PGPASSWORD': self.password}
        return {}


class Ldap(Source):
    """Dump a OpenLDAP database using slapcat to a filename in the local repository.
    Must be run on the LDAP server."""
    parameters = Source.parameters + [
        Parameter('destination_path', help_str='filename of the dump (not an absolute path)'),
        Parameter('use_sudo', help_str='use sudo to perform the dump (yes/no)', converter=bool_setting),
        Parameter('data_directory', help_str='your LDAP base (if you want to restrict the dump)'),
        Parameter('ldap_base', help_str='your LDAP base dn (if you want to restrict the dump)'),
        Parameter('database', help_str='database number (default: 1)', converter=int),
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the slapcat executable (default: "slapcat")'),
        Parameter('restore_executable', converter=check_executable,
                  help_str='path of the slapadd executable (default: "slapadd")'),
    ]

    def __init__(self, name, local_repository, destination_path='ldap.ldif', dump_executable='slapcat',
                 use_sudo=False, restore_executable='slapadd', database=1, ldap_base=None, **kwargs):
        super(Ldap, self).__init__(name, local_repository, **kwargs)
        self.destination_path = destination_path
        self.dump_executable = dump_executable
        self.restore_executable = restore_executable
        self.use_sudo = use_sudo
        self.ldap_base = ldap_base
        self.database = database

    def backup(self):
        filename = os.path.join(self.local_repository.import_data_path, self.destination_path)
        self.ensure_dir(filename, parent=True)
        cmd = []
        if self.use_sudo:
            cmd += ['sudo']
        cmd += [self.dump_executable]
        if self.ldap_base:
            cmd += ['-b', self.ldap_base]
        cmd += ['-n', str(self.database)]
        self.execute_command(cmd)
        if not self.can_execute_command(cmd + ['>', filename]):
            filename = os.devnull  # run the dump even in dry mode
        with open(filename, 'wb') as fd:
            p = subprocess.Popen(cmd, stdout=fd, stderr=self.stderr)
            p.communicate()

    def restore(self):
        filename = os.path.join(self.local_repository.import_data_path, self.destination_path)
        if not os.path.isfile(filename):
            return
        prefix = []
        if self.use_sudo:
            prefix += ['sudo']
        # identify the database folder
        p = subprocess.Popen(prefix + [self.dump_executable, '-n', '0'], stdout=subprocess.PIPE, stderr=self.stderr)
        stdout, __ = p.communicate()
        database_folder = self.get_database_folder(io.BytesIO(stdout), str(self.database))
        if database_folder is None:
            raise IOError('Unable to find database folder for database %s' % self.database)
        stat_info = os.stat(database_folder)
        uid = stat_info.st_uid
        gid = stat_info.st_gid
        user = pwd.getpwuid(uid)[0]
        group = grp.getgrgid(gid)[0]

        self.execute_command(prefix + ['service', 'slapd', 'stop'])
        self.execute_command(prefix + ['rm', '-rf', database_folder])
        self.execute_command(prefix + ['mkdir', '-p', database_folder])
        self.execute_command(prefix + [self.restore_executable, '-l', filename, ])
        self.execute_command(prefix + ['chown', '-R', '%s:%s' % (user, group), database_folder])
        self.execute_command(prefix + ['service', 'slapd', 'start'])

    @staticmethod
    def get_database_folder(ldif_config, database_number):
        parser = LDIFParser(ldif_config)
        regexp = re.compile('^olcDatabase=\{%s\}(.*),cn=config$' % database_number)
        for dn, entry in parser.parse():
            if not regexp.match(dn):
                continue
            return entry.get('olcDbDirectory', [None])[0]
        return None


class Dovecot(Source):
    """Dump a OpenLDAP database using slapcat to a filename in the local repository.
    Must be run on the LDAP server."""
    parameters = Source.parameters + [
        Parameter('destination_path', help_str='dirname of the dump (not an absolute path)'),
        Parameter('mailbox', help_str='only sync this mailbox name'),
        Parameter('socket', help_str='The option\'s argument is either an absolute path to a local UNIX domain socket,'
                                     ' or a hostname and port (hostname:port), in order to connect a remote host via a'
                                     ' TCP socket.'),
        Parameter('user_mask', help_str='only sync this user ("*" and "?" wildcards can be used).'),
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the slapcat executable (default: "doveadm")'),
    ]

    def __init__(self, name, local_repository, destination_path='dovecot', dump_executable='doveadm',
                 mailbox=None, user_mask=None, socket=None, **kwargs):
        super(Dovecot, self).__init__(name, local_repository, **kwargs)
        self.socket = socket
        self.destination_path = destination_path
        self.dump_executable = dump_executable
        self.mailbox = mailbox
        self.user_mask = user_mask

    def backup(self):
        self.perform_action(restore=False)

    def restore(self):
        self.perform_action(restore=True)

    def perform_action(self, restore):
        dirname = os.path.join(self.local_repository.import_data_path, self.destination_path)
        self.ensure_dir(dirname)
        cmd = [self.dump_executable, 'backup', ]
        if restore:
            cmd += ['-R']
        if self.mailbox:
            cmd += ['-m', self.mailbox, ]
        if self.socket:
            cmd += ['-S', self.socket]
        if self.user_mask is None:
            cmd += ['-A']
        else:
            cmd += ['-u', self.user_mask]
        cmd += [dirname]
        self.execute_command(cmd)
