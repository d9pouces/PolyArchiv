# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import io
import logging.config
import os
import shutil

from polyarchiv.locals import FileRepository
from polyarchiv.sources import LocalFiles, PostgresSQL, MySQL, Ldap
from polyarchiv.tests.test_base import FileTestCase

__author__ = 'Matthieu Gallet'

log = {'version': 1, 'disable_existing_loggers': True,
       'formatters': {'color': {'()': 'logging.Formatter', 'format': "%(log_color)s%(message)s%(reset)s"}},
       'handlers': {'stream': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'color'}},
       'loggers': {'polyarchiv': {'handlers': ['stream', ], 'level': 'DEBUG', 'propagate': False}}}
logging.config.dictConfig(log)


class TestSources(FileTestCase):
    dirpath = os.path.join(os.path.dirname(__file__), 'tests')

    def setUp(self):
        super(TestSources, self).setUp()
        self.local_repository = FileRepository('test_repo', local_path=self.local_repository_path, command_display=True,
                                               command_keep_output=True)

    def test_rsync(self):
        source = LocalFiles('rsync', self.local_repository, destination_path='rsync',
                            source_path=self.original_dir_path)
        source.backup()
        self.assertEqualPaths(self.original_dir_path, os.path.join(self.local_repository.export_data_path, 'rsync'))
        shutil.copy2(__file__, os.path.join(self.original_dir_path, 'test2.py'))
        os.remove(os.path.join(self.original_dir_path, 'test.py'))
        source.backup()
        self.assertEqualPaths(self.original_dir_path, os.path.join(self.local_repository.export_data_path, 'rsync'))

        source = LocalFiles('rsync', self.local_repository, destination_path='rsync',
                            source_path=self.copy_dir_path)
        source.restore()
        self.assertEqualPaths(self.original_dir_path, self.copy_dir_path)

    def test_postgresql(self):
        filename = 'postgresql.sql'
        source = PostgresSQL('postgresql', self.local_repository,
                             destination_path=filename, database='testdb',
                             host='localhost', port='5432', user='test', password='testtest')
        source.backup()
        dst_path = os.path.join(self.local_repository.export_data_path, filename)
        src_path = '%s/samples/postgresql.sql' % os.path.dirname(__file__)
        dst_content = self.get_sql_content(dst_path)
        src_content = self.get_sql_content(src_path)
        self.assertEqual(dst_content, src_content)
        source = PostgresSQL('postgresql', self.local_repository,
                             destination_path=filename, database='restoredb',
                             host='localhost', port='5432', user='test', password='testtest')
        source.restore()
        source.backup()
        dst_path = os.path.join(self.local_repository.export_data_path, filename)
        dst_content = self.get_sql_content(dst_path)
        self.assertEqual(dst_content, src_content)

    def test_mysql(self):
        filename = 'mysql.sql'
        source = MySQL('mysql', self.local_repository,
                       destination_path=filename, database='testdb',
                       host='localhost', port='3306', user='test', password='testtest')
        source.backup()
        dst_path = os.path.join(self.local_repository.export_data_path, filename)
        src_path = '%s/samples/mysql.sql' % os.path.dirname(__file__)
        dst_content = self.get_sql_content(dst_path)
        src_content = self.get_sql_content(src_path)
        self.assertEqual(dst_content, src_content)
        source = MySQL('mysql', self.local_repository,
                       destination_path=filename, database='restoredb',
                       host='localhost', port='3306', user='test', password='testtest')
        source.restore()
        source.backup()
        dst_path = os.path.join(self.local_repository.export_data_path, filename)
        dst_content = self.get_sql_content(dst_path)
        self.assertEqual(dst_content, src_content)

    def test_read_ldif(self):
        src_path = '%s/samples/config.ldif' % os.path.dirname(__file__)
        with open(src_path, 'rb') as fd:
            content = fd.read()
        self.assertIsNone(Ldap.get_database_folder(io.BytesIO(content), '-1'))
        self.assertIsNone(Ldap.get_database_folder(io.BytesIO(content), '0'))
        self.assertEqual('/var/lib/ldap', Ldap.get_database_folder(io.BytesIO(content), '1'))

    def test_ldap(self):
        filename = 'ldap.ldif'
        source = Ldap('ldap', self.local_repository, destination_path=filename, use_sudo=True)
        source.backup()
        src_path = '%s/samples/ldap.ldif' % os.path.dirname(__file__)
        dst_path = os.path.join(self.local_repository.export_data_path, filename)
        src_content = self.get_ldif_content(src_path)
        dst_content = self.get_ldif_content(dst_path)
        self.assertEqual(src_content, dst_content)
        source.restore()
        source.backup()
        dst_path = os.path.join(self.local_repository.export_data_path, filename)
        dst_content = self.get_ldif_content(dst_path)
        self.assertEqual(src_content, dst_content)

    def test_dovecot(self):
        pass

    @staticmethod
    def get_sql_content(dst_path):
        def valid(x):
            if 'Server version' in x or 'Dump' in x or 'Database' in x or 'MySQL dump ' in x:
                return False
            return True

        with codecs.open(dst_path, 'r', encoding='latin1') as fd:
            lines = [line for line in fd if valid(line.strip())]
        lines.sort()
        return '\n'.join(lines)

    @staticmethod
    def get_ldif_content(dst_path):
        def valid(x):
            if ' 2016' in x or 'UUID' in x:
                return False
            return True

        with codecs.open(dst_path, 'r', encoding='latin1') as fd:
            lines = [line for line in fd if valid(line.strip())]
        return '\n'.join(lines)
