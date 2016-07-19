# -*- coding: utf-8 -*-
import datetime
import logging

from polyarchiv.collect_points import CollectPoint
from polyarchiv.remotes import RemoteRepository
from polyarchiv.repository import RepositoryInfo
from polyarchiv.runner import Runner
from polyarchiv.sources import Source
from polyarchiv.termcolor import cprint, RED, YELLOW, GREEN, BOLD, CYAN

__author__ = 'Matthieu Gallet'

logger = logging.getLogger('polyarchiv.show')


def show_collect_point(collect_point, engines_file=None):
    available_collect_point_engines, available_source_engines, __, __ = Runner.find_available_engines(engines_file)

    # ##################################################################################################################
    assert isinstance(collect_point, CollectPoint)
    cprint('collect point %s selected' % collect_point.name, CYAN)
    if collect_point.__class__ in available_collect_point_engines:
        engine = available_collect_point_engines[collect_point.__class__]
    else:
        engine = '%s.%s' % (collect_point.__class__.__module__, collect_point.__class__.__name__)
    logger.debug('engine: %s' % engine)
    if collect_point.__doc__:
        logger.debug(collect_point.__doc__)
    # ##################################################################################################################
    for source in collect_point.sources:
        assert isinstance(source, Source)
        cprint('  * source %s added to %s' % (source.name, collect_point.name), CYAN)
        if source.__class__ in available_source_engines:
            engine = available_source_engines[source.__class__]
        else:
            engine = '%s.%s' % (source.__class__.__module__, source.__class__.__name__)
        logger.debug('engine: %s' % engine)
        if source.__doc__:
            logger.debug(source.__doc__)
    # ##################################################################################################################
    try:
        info = collect_point.get_info()
    except ValueError as e:
        cprint('Unable to retrieve more information from the collect point: %s' % e, RED)
        return
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        cprint('No successful local collect', RED)
    else:
        now = datetime.datetime.now()
        out_of_date = collect_point.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            cprint('Last local collect is out of date: %s' % info.last_success, YELLOW, BOLD)
        else:
            cprint('Last local collect is recent enough: %s' % info.last_success, GREEN)
    if info.last_state_valid is False:
        cprint('The last backup has failed. %s' % info.last_message, RED)


def show_remote_repository(remote_repository, engines_file=None):
    __, __, available_remote_engines, __ = Runner.find_available_engines(engines_file)
    assert isinstance(remote_repository, RemoteRepository)
    cprint('remote repository %s selected' % remote_repository.name, CYAN)
    if remote_repository.__class__ in available_remote_engines:
        engine = available_remote_engines[remote_repository.__class__]
    else:
        engine = '%s.%s' % (remote_repository.__class__.__module__, remote_repository.__class__.__name__)
    logger.debug('engine: %s' % engine)
    if remote_repository.__doc__:
        logger.debug(remote_repository.__doc__)


def show_remote_collect_point(collect_point, remote_repository):
    assert isinstance(collect_point, CollectPoint)
    assert isinstance(remote_repository, RemoteRepository)
    cprint('  * remote repository %s selected on collect point %s' % (remote_repository.name, collect_point.name),
           CYAN)
    try:
        info = remote_repository.get_info(collect_point)
    except ValueError as e:
        cprint('Unable to retrieve more information from the remote repository: %s' % e, RED)
        return
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        cprint('No successful remote backup for %s' % remote_repository.name, RED)
    else:
        now = datetime.datetime.now()
        out_of_date = collect_point.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            cprint('Last local collect is out of date on %s: %s' % (remote_repository.name, info.last_success), YELLOW,
                   BOLD)
        else:
            cprint('Last local collect is recent enough on %s: %s' % (remote_repository.name, info.last_success), GREEN)
    if info.last_state_valid is False:
        cprint('The last collect has failed on %s. %s' % (remote_repository.name, info.last_message), RED)
