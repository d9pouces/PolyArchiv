# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import logging

from polyarchiv.locals import LocalRepository
from polyarchiv.remotes import RemoteRepository
from polyarchiv.repository import RepositoryInfo

__author__ = 'Matthieu Gallet'

logger = logging.getLogger('polyarchiv.show')


def check_local_repository(values, local_repository):
    assert isinstance(local_repository, LocalRepository)
    name = local_repository.name
    try:
        info = local_repository.get_info()
    except ValueError as e:
        values['return_code'] = 2
        values['return_text'] += ['unable to check status of %s: %s' % (name, e)]
        return
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        values['return_code'] = 2
        values['return_text'] += ['no successful backup of %s' % name]
    else:
        now = datetime.datetime.now()
        out_of_date = local_repository.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            values['return_code'] = max(values['return_code'], 1)
            values['return_text'] += ['the last backup of %s is out of date: %s' % (name, info.last_success)]
    if info.last_state_valid is False:
        values['return_code'] = 2
        values['return_text'] += ['the last backup of %s has failed. %s' % (name, info.last_message)]


def check_remote_local_repository(values, local_repository, remote_repository):
    assert isinstance(local_repository, LocalRepository)
    assert isinstance(remote_repository, RemoteRepository)
    name = '%s:%s' % (local_repository.name, remote_repository.name)
    try:
        info = remote_repository.get_info(local_repository)
    except ValueError as e:
        values['return_code'] = 2
        values['return_text'] += ['unable to check status of %s: %s' % (name, e)]
        return
    assert isinstance(info, RepositoryInfo)
    if info.last_success is None:
        values['return_code'] = 2
        values['return_text'] += ['no successful backup of %s' % name]
    else:
        now = datetime.datetime.now()
        out_of_date = local_repository.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            values['return_code'] = max(values['return_code'], 1)
            values['return_text'] += ['the last backup of %s is out of date: %s' % (name, info.last_success)]
    if info.last_state_valid is False:
        values['return_code'] = 2
        values['return_text'] += ['the last backup of %s has failed. %s' % (name, info.last_message)]
