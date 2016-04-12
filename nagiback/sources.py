# -*- coding=utf-8 -*-
"""Base backup sources.

  * MySQL
  * PostgreSQL
  * SQlite
  * raw files

"""
from __future__ import unicode_literals
import logging

import os
import subprocess

from nagiback.conf import Parameter, bool_setting, check_directory, check_executable
from nagiback.locals import LocalRepository
from nagiback.repository import ParameterizedObject

__author__ = 'mgallet'
logger = logging.getLogger('nagiback.sources')


class Source(ParameterizedObject):
    """base source class"""
    parameters = ParameterizedObject.parameters + []

    # noinspection PyUnusedLocal
    def __init__(self, name, local_repository, **kwargs):
        super(Source, self).__init__(name)
        assert isinstance(local_repository, LocalRepository)
        self.local_repository = local_repository

    def backup(self):
        """Backup data corresponding to this source"""
        raise NotImplementedError

    def get_info(self, name, kind='sources'):
        return self.local_repository.get_info(name, kind=kind)

    def set_info(self, info, name, kind='sources'):
        return self.local_repository.set_info(info, name, kind=kind)


class RSync(Source):
    """copy all files from the destination to the backup using rsync.
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
        Parameter('preserve_hard_links', converter=bool_setting, help_str='preserve hard links'),
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
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        source = self.source_path
        if not source.endswith(os.path.sep):
            source += os.path.sep
        if not dirname.endswith(os.path.sep):
            dirname += os.path.sep
        cmd += [source, dirname]
        logger.info(' '.join(cmd))
        subprocess.check_call(cmd)


class MySQL(Source):
    parameters = Source.parameters + [
        Parameter('host', help_str='database host'),
        Parameter('port', converter=int, help_str='database port'),
        Parameter('user', help_str='database user'),
        Parameter('password', help_str='database password'),
        Parameter('database', help_str='name of the backuped database'),
        Parameter('destination_path', help_str='relative path of the backup destination (e.g. "database.sql")'),
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the mysqldump executable (default: "mysqldump")'),
    ]

    def __init__(self, name, local_repository, host='localhost', port='3306', user='', password='', database='',
                 destination_path='', dump_executable='mysqldump', **kwargs):
        super(MySQL, self).__init__(name, local_repository, **kwargs)
        self.dump_executable = dump_executable
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.destination_path = destination_path

    def backup(self):
        filename = os.path.join(self.local_repository.get_cwd(), self.destination_path)
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        cmd = self.get_dump_cmd_list()
        cmd = [x % self.db_options for x in cmd]
        env = os.environ.copy()
        env.update(self.get_env())
        logger.info(' '.join(cmd))
        if filename is not None:
            with open(filename, 'wb') as fd:
                p = subprocess.Popen(cmd, env=env, stdout=fd, stderr=subprocess.PIPE)
        else:
            p = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE)
        p.communicate()

    @property
    def db_options(self):
        return {'HOST': self.host, 'PORT': self.port, 'USER': self.user, 'PASSWORD': self.password,
                'NAME': self.database}

    def get_dump_cmd_list(self):
        """ :return:
        :rtype: :class:`list` of :class:`str`
        """
        command = [self.dump_executable, '--user', '%(USER)s', '--password=%(PASSWORD)s']
        if self.db_options.get('HOST'):
            command += ['--host', '%(HOST)s']
        if self.db_options.get('PORT'):
            command += ['--port', '%(PORT)s']
        command += ['%(NAME)s']
        return command

    def get_env(self):
        """Extra environment variables to be passed to shell execution"""
        return {}


class PostgresSQL(MySQL):
    parameters = MySQL.parameters[:-1] + [
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the pg_dump executable (default: "pg_dump")'),
    ]

    def __init__(self, name, local_repository, port='5432', dump_executable='pg_dump', **kwargs):
        super(PostgresSQL, self).__init__(name, local_repository, port=port, dump_executable=dump_executable, **kwargs)

    def get_dump_cmd_list(self):
        command = [self.dump_executable, '--username', '%(USER)s']
        if self.db_options.get('HOST'):
            command += ['--host', '%(HOST)s']
        if self.db_options.get('PORT'):
            command += ['--port', '%(PORT)s']
        command += ['%(NAME)s']
        return command

    def get_env(self):
        """Extra environment variables to be passed to shell execution"""
        return {'PGPASSWORD': '%(PASSWORD)s' % self.db_options}


class Ldap(Source):
    parameters = Source.parameters + [
        Parameter('database', help_str='number of the database (usually 0 and 1)'),
        Parameter('destination_path', help_str='filename of the dump (not an absolute path)'),
        Parameter('dump_executable', converter=check_executable,
                  help_str='path of the slapcat executable (default: "slapcat")'),
    ]

    def __init__(self, name, local_repository, destination_path='ldap.ldif', database='1', dump_executable='slapcat',
                 **kwargs):
        super(Ldap, self).__init__(name, local_repository, **kwargs)
        self.destination_path = destination_path
        self.database = database
        self.dump_executable = dump_executable

    def backup(self):
        filename = os.path.join(self.local_repository.get_cwd(), self.destination_path)
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        cmd = [self.dump_executable, '-n', self.database, ]
        logger.info(' '.join(cmd))
        if filename is not None:
            with open(filename, 'wb') as fd:
                p = subprocess.Popen(cmd, stdout=fd, stderr=subprocess.PIPE)
        else:
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        p.communicate()
