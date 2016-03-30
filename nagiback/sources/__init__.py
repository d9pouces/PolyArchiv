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

__author__ = 'mgallet'


class Source(object):
    """base source class"""

    def __init__(self, local_directory):
        self.local_directory = local_directory

    def run(self):
        raise NotImplementedError


class MySQL(Source):
    def __init__(self, local_repository, host='localhost', port='5432', user='', password='', name='',
                 destination_path=''):
        super(MySQL, self).__init__(local_repository)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.name = name
        self.destination_path = destination_path

    def run(self):
        pass

    def dump(self, filename):
        cmd = self.dump_cmd_list()
        cmd = [x % self.db_options for x in cmd]
        env = os.environ.copy()
        env.update(self.get_env())
        if filename is not None:
            with open(filename, 'wb') as fd:
                p = subprocess.Popen(cmd, env=env, stdout=fd)
        else:
            p = subprocess.Popen(cmd, env=env)
        p.communicate()


    def dump_cmd_list(self):
        """ :return:
        :rtype: :class:`list` of :class:`str`
        """
        command = ['mysqldump', '--user', '%(USER)s', '--password', '%(PASSWORD)s']
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

    def __init__(self, local_repository, host='localhost', port='5432', user='', password='', name='',
                 destination_path=''):
        super(PostgresSQL, self).__init__(local_repository)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.name = name
        self.destination_path = destination_path

    def run(self):
        pass

class PostgreSQL(MySQL):
    """ dump the content of a PostgreSQL database, with `pg_dump`"""

    def dump_cmd_list(self):
        command = ['pg_dump', '--username', '%(USER)s']
        if self.db_options.get('HOST'):
            command += ['--host', '%(HOST)s']
        if self.db_options.get('PORT'):
            command += ['--port', '%(PORT)s']
        if settings.FLOOR_BACKUP_SINGLE_TRANSACTION:
            command += ['--single-transaction']
        command += ['%(NAME)s']
        return command

    def get_env(self):
        """Extra environment variables to be passed to shell execution"""
        return {'PGPASSWORD': '%(PASSWORD)s' % self.db_options}

class SQLite(BaseDumper):
    """copy the SQLite database to another file, or write its content to `stdout`"""

    def dump(self, filename):
        if filename is None:
            p = subprocess.Popen(['cat', self.db_options['NAME']])
            p.communicate()
        else:
            shutil.copy(self.db_options['NAME'], filename)

