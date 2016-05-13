# -*- coding: utf-8 -*-
import datetime
import logging

from pkg_resources import iter_entry_points

from polyarchiv.locals import LocalRepository
from polyarchiv.remotes import RemoteRepository
from polyarchiv.repository import RepositoryInfo
from polyarchiv.sources import Source
from polyarchiv.termcolor import cprint, RED, YELLOW, GREEN, BOLD, CYAN

__author__ = 'Matthieu Gallet'

logger = logging.getLogger('polyarchiv.show')


def show_local_repository(local_repository):
    available_local_engines = {x.load(): x.name.lower() for x in iter_entry_points('polyarchiv.locals')}
    available_source_engines = {x.load(): x.name.lower() for x in iter_entry_points('polyarchiv.sources')}

    # ##################################################################################################################
    assert isinstance(local_repository, LocalRepository)
    cprint('local repository %s selected' % local_repository.name, CYAN)
    if local_repository.__class__ in available_local_engines:
        engine = available_local_engines[local_repository.__class__]
    else:
        engine = '%s.%s' % (local_repository.__class__.__module__, local_repository.__class__.__name__)
    logger.debug('engine: %s' % engine)
    if local_repository.__doc__:
        logger.debug(local_repository.__doc__)
    # ##################################################################################################################
    for source in local_repository.sources:
        assert isinstance(source, Source)
        cprint('  * source %s added to %s' % (source.name, local_repository.name), CYAN)
        if source.__class__ in available_source_engines:
            engine = available_source_engines[source.__class__]
        else:
            engine = '%s.%s' % (source.__class__.__module__, source.__class__.__name__)
        logger.debug('engine: %s' % engine)
        if source.__doc__:
            logger.debug(source.__doc__)
    # ##################################################################################################################
    try:
        info = local_repository.get_info()
    except ValueError as e:
        cprint('Unable to retrieve more information from the local repository: %s' % e, RED)
        return
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        cprint('No successful local backup', RED)
    else:
        now = datetime.datetime.now()
        out_of_date = local_repository.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            cprint('Last local backup is out of date: %s' % info.last_success, YELLOW, BOLD)
        else:
            cprint('Last local backup is recent enough: %s' % info.last_success, GREEN)
    if info.last_state_valid is False:
        cprint('The last backup has failed. %s' % info.last_message, RED)


def show_remote_repository(remote_repository):
    available_remote_engines = {x.load(): x.name.lower() for x in iter_entry_points('polyarchiv.remotes')}
    assert isinstance(remote_repository, RemoteRepository)
    cprint('remote repository %s selected' % remote_repository.name, CYAN)
    if remote_repository.__class__ in available_remote_engines:
        engine = available_remote_engines[remote_repository.__class__]
    else:
        engine = '%s.%s' % (remote_repository.__class__.__module__, remote_repository.__class__.__name__)
    logger.debug('engine: %s' % engine)
    if remote_repository.__doc__:
        logger.debug(remote_repository.__doc__)


def show_remote_local_repository(local_repository, remote_repository):
    assert isinstance(local_repository, LocalRepository)
    assert isinstance(remote_repository, RemoteRepository)
    cprint('  * remote repository %s selected on local repository %s' % (remote_repository.name, local_repository.name),
           CYAN)
    try:
        info = remote_repository.get_info(local_repository)
    except ValueError as e:
        cprint('Unable to retrieve more information from the remote repository: %s' % e, RED)
        return
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        cprint('No successful remote backup for %s' % remote_repository.name, RED)
    else:
        now = datetime.datetime.now()
        out_of_date = local_repository.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            cprint('Last local backup is out of date on %s: %s' % (remote_repository.name, info.last_success), YELLOW,
                   BOLD)
        else:
            cprint('Last local backup is recent enough on %s: %s' % (remote_repository.name, info.last_success), GREEN)
    if info.last_state_valid is False:
        cprint('The last backup has failed on %s. %s' % (remote_repository.name, info.last_message), RED)
