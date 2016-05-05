# -*- coding=utf-8 -*-
"""Base backup sources.

  * MySQL
  * PostgreSQL
  * SQlite
  * raw files

"""
from __future__ import unicode_literals

import os
import subprocess

from polyarchiv.conf import Parameter, bool_setting, check_directory, check_executable
from polyarchiv.locals import LocalRepository
from polyarchiv.repository import ParameterizedObject
from polyarchiv.termcolor import YELLOW
from polyarchiv.termcolor import cprint

__author__ = 'mgallet'


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

    def get_info(self, name, kind='sources'):
        return self.local_repository.get_info(name, kind=kind)

    def set_info(self, info, name, kind='sources'):
        return self.local_repository.set_info(info, name, kind=kind)


class RSync(Source):
    """copy all files from the given source_path to the local repository using rsync.
    The destination is a folder inside the local repository.
    """
    parameters = Source.parameters + [
        Parameter('source_path', converter=check_directory, help_str='original folder to backup'),
        Parameter('destination_path', help_str='destination folder (relative path, e.g. "./files")'),
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
        :param include: don't exclude files matching PATTERN. If PATTERN starts with '@', it must be the absolute path of
            a file (cf. the --include-from option from rsync)
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
        if self.exclude and self.exclude.startswith('@'):
            cmd += ['--exclude-from', self.exclude[1:]]
        elif self.exclude:
            cmd += ['--exclude', self.exclude]
        if self.include and self.include.startswith('@'):
            cmd += ['--include-from', self.include[1:]]
        elif self.include:
            cmd += ['--include', self.include]
        dirname = os.path.join(self.local_repository.get_cwd(), self.destination_path)
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
        dirname = os.path.join(self.local_repository.get_cwd(), self.destination_path)
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
        Parameter('user', help_str='database user'),
        Parameter('password', help_str='database password'),
        Parameter('database', help_str='name of the backuped database'),
        Parameter('destination_path', help_str='relative path of the backup destination (e.g. "database.sql")'),
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the mysqldump executable (default: "mysqldump")'),
        Parameter('restore_executable', converter=check_executable,
                  help_str='path of the mysql executable (default: "mysql")'),
    ]

    def __init__(self, name, local_repository, host='localhost', port='3306', user='', password='', database='',
                 destination_path='', dump_executable='mysqldump', restore_executable='mysql', **kwargs):
        super(MySQL, self).__init__(name, local_repository, **kwargs)
        self.restore_executable = restore_executable
        self.dump_executable = dump_executable
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.destination_path = destination_path

    def backup(self):
        filename = os.path.join(self.local_repository.get_cwd(), self.destination_path)
        self.ensure_dir(filename, parent=True)
        cmd = self.get_dump_cmd_list()
        cmd = [x % self.db_options for x in cmd]
        env = os.environ.copy()
        env.update(self.get_env())
        if self.command_display:
            for k, v in self.get_env().items():
                cprint('%s=%s' % (k, v), YELLOW)
        if self.can_execute_command(cmd + ['>', filename]):
            with open(filename, 'wb') as fd:
                p = subprocess.Popen(cmd, env=env, stdout=fd, stderr=self.stderr)
                p.communicate()
        else:
            with open(os.devnull, 'wb') as fd:
                p = subprocess.Popen(cmd, env=env, stdout=fd, stderr=self.stderr)
                p.communicate()
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, cmd[0])

    def restore(self):
        filename = os.path.join(self.local_repository.get_cwd(), self.destination_path)
        if not os.path.isfile(filename):
            return
        cmd = self.get_dump_cmd_list()
        cmd = [x % self.db_options for x in cmd]
        env = os.environ.copy()
        env.update(self.get_env())
        if self.command_display:
            for k, v in self.get_env():
                cprint('%s=%s' % (k, v), YELLOW)
        with open(filename, 'rb') as fd:
            self.execute_command(cmd, env=env, stdin=fd, stderr=self.stderr, stdout=self.stdout)

    @property
    def db_options(self):
        return {'HOST': self.host, 'PORT': self.port, 'USER': self.user, 'PASSWORD': self.password,
                'NAME': self.database}

    def get_dump_cmd_list(self):
        """ :return:
        :rtype: :class:`list` of :class:`str`
        """
        command = [self.dump_executable, '--user=%(USER)s', '--password=%(PASSWORD)s']
        if self.db_options.get('HOST'):
            command += ['--host=%(HOST)s']
        if self.db_options.get('PORT'):
            command += ['--port=%(PORT)s']
        command += ['%(NAME)s']
        return command

    def get_restore_cmd_list(self):
        """ :return:
        :rtype: :class:`list` of :class:`str`
        """
        command = [self.restore_executable, '--user=%(USER)s', '--password=%(PASSWORD)s']
        if self.db_options.get('HOST'):
            command += ['--host=%(HOST)s']
        if self.db_options.get('PORT'):
            command += ['--port=%(PORT)s']
        command += ['%(NAME)s']
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

    def __init__(self, name, local_repository, port='5432', dump_executable='pg_dump', **kwargs):
        super(PostgresSQL, self).__init__(name, local_repository, port=port, dump_executable=dump_executable, **kwargs)

    def get_dump_cmd_list(self):
        command = [self.dump_executable, '--username=%(USER)s']
        if self.db_options.get('HOST'):
            command += ['--host=%(HOST)s']
        if self.db_options.get('PORT'):
            command += ['--port=%(PORT)s']
        command += ['%(NAME)s']
        return command

    def get_restore_cmd_list(self):
        command = [self.restore_executable, '--username=%(USER)s']
        if self.db_options.get('HOST'):
            command += ['--host=%(HOST)s']
        if self.db_options.get('PORT'):
            command += ['--port=%(PORT)s']
        command += ['%(NAME)s']
        return command

    def get_env(self):
        """Extra environment variables to be passed to shell execution"""
        return {'PGPASSWORD': '%(PASSWORD)s' % self.db_options}


class Ldap(Source):
    """Dump a OpenLDAP database using slapcat to a filename in the local repository"""
    parameters = Source.parameters + [
        Parameter('database', help_str='number of the database (usually 0 and 1)'),
        Parameter('destination_path', help_str='filename of the dump (not an absolute path)'),
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the slapcat executable (default: "slapcat")'),
        Parameter('restore_executable', converter=check_executable,
                  help_str='path of the slapadd executable (default: "slapadd")'),
    ]

    def __init__(self, name, local_repository, destination_path='ldap.ldif', database=None, dump_executable='slapcat',
                 restore_executable='slapadd', **kwargs):
        super(Ldap, self).__init__(name, local_repository, **kwargs)
        self.destination_path = destination_path
        self.database = database
        self.dump_executable = dump_executable
        self.restore_executable = restore_executable

    def backup(self):
        filename = os.path.join(self.local_repository.get_cwd(), self.destination_path)
        self.ensure_dir(filename, parent=True)
        cmd = [self.dump_executable, '-l', filename]
        if self.database:
            cmd += ['-n', self.database]
        self.execute_command(cmd)

    def restore(self):
        filename = os.path.join(self.local_repository.get_cwd(), self.destination_path)
        if not os.path.isfile(filename):
            return
        self.execute_command(['service' 'slapd', 'stop'])
        self.execute_command([self.restore_executable, '-l', filename, ])
        self.execute_command(['service' 'slapd', 'start'])
