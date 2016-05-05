# -*- coding: utf-8 -*-
import logging
import datetime
from polyarchiv.conf import Parameter
from polyarchiv.locals import LocalRepository
from polyarchiv.remotes import RemoteRepository
from polyarchiv.repository import RepositoryInfo
from polyarchiv.sources import Source

__author__ = 'Matthieu Gallet'

logger = logging.getLogger('polyarchiv.show')


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
    info = local_repository.get_info()
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        logger.critical('No successful local backup')
    else:
        now = datetime.datetime.now()
        out_of_date = local_repository.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            logger.critical('Last local backup is out of date: %s' % info.last_success)
        else:
            logger.info('Last local backup is recent enough: %s' % info.last_success)
    if info.last_state_valid is False:
        logger.critical('The last backup has failed. %s' % info.last_message)


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
    info = remote_repository.get_info(local_repository)
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        logger.critical('No successful remote backup for %s' % remote_repository.name)
    else:
        now = datetime.datetime.now()
        out_of_date = local_repository.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            logger.critical('Last local backup is out of date on %s: %s' % (remote_repository.name, info.last_success))
        else:
            logger.info('Last local backup is recent enough on %s: %s' % (remote_repository.name, info.last_success))
    if info.last_state_valid is False:
        logger.critical('The last backup has failed on %s. %s' % (remote_repository.name, info.last_message))
