# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging.config
import os
from unittest import TestCase

__author__ = 'Matthieu Gallet'

log = {'version': 1, 'disable_existing_loggers': True,
       'formatters': {'color': {'()': 'logging.Formatter', 'format': "%(log_color)s%(message)s%(reset)s"}},
       'handlers': {'stream': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'color'}},
       'loggers': {'polyarchiv': {'handlers': ['stream', ], 'level': 'DEBUG', 'propagate': False}}}
logging.config.dictConfig(log)

from polyarchiv.runner import Runner
from polyarchiv.locals import LocalRepository
from polyarchiv.sources import RSync, PostgresSQL, MySQL


class TestSources(TestCase):
    dirpath = os.path.join(os.path.dirname(__file__), 'samples')
    #
    # def test_rsync(self):
    #     runner = Runner([self.dirpath])
    #     local_repository = runner.local_repositories['app1']
    #     assert isinstance(local_repository, LocalRepository)
    #     rsync = local_repository.sources[2]
    #     assert isinstance(rsync, RSync)
    #     rsync.backup()
    #
    # def test_postgresql(self):
    #     runner = Runner([self.dirpath])
    #     local_repository = runner.local_repositories['app1']
    #     assert isinstance(local_repository, LocalRepository)
    #     postgres = local_repository.sources[0]
    #     assert isinstance(postgres, PostgresSQL)
    #     postgres.backup()
    #
    # def test_mysql(self):
    #     runner = Runner([self.dirpath])
    #     local_repository = runner.local_repositories['app1']
    #     assert isinstance(local_repository, LocalRepository)
    #     mysql = local_repository.sources[1]
    #     assert isinstance(mysql, MySQL)
    #     mysql.backup()
