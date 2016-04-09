# -*- coding: utf-8 -*-
import logging
from nagiback.conf import Parameter
from nagiback.locals import LocalRepository
from nagiback.remotes import RemoteRepository
from nagiback.sources import Source

__author__ = 'Matthieu Gallet'

logger = logging.getLogger('nagiback.show')


def show_local_repository(local_repository):
    assert isinstance(local_repository, LocalRepository)
    logger.debug('====================================================')
    logger.error('local repository %s selected' % local_repository.name)
    engine = '%s.%s' % (local_repository.__class__.__module__, local_repository.__class__.__name__)
    logger.debug('engine: %s' % engine)
    for source in local_repository.sources:
        assert isinstance(source, Source)
        logger.debug('----------------------------------------------------')
        logger.error('source %s added to %s' % (source.name, local_repository.name))
        engine = '%s.%s' % (source.__class__.__module__, source.__class__.__name__)
        logger.debug('engine: %s' % engine)


def show_remote_repository(remote_repository):
    assert isinstance(remote_repository, RemoteRepository)
    logger.debug('====================================================')
    logger.error('remote repository %s selected' % remote_repository.name)
    engine = '%s.%s' % (remote_repository.__class__.__module__, remote_repository.__class__.__name__)
    logger.debug('engine: %s' % engine)


def show_remote_local_repository(local_repository, remote_repository):
    assert isinstance(local_repository, LocalRepository)
    assert isinstance(remote_repository, RemoteRepository)
    logger.debug('====================================================')
    logger.error('remote repository %s selected on local repository %s' % (remote_repository.name,
                                                                           local_repository.name))
