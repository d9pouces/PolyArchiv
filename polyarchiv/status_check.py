# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import logging

from polyarchiv.collect_points import CollectPoint
from polyarchiv.backup_points import BackupPoint
from polyarchiv.points import PointInfo

__author__ = 'Matthieu Gallet'

logger = logging.getLogger('polyarchiv.show')


def check_collect_point(values, collect_point):
    assert isinstance(collect_point, CollectPoint)
    name = collect_point.name
    try:
        info = collect_point.get_info()
    except ValueError as e:
        values['return_code'] = 2
        values['return_text'] += ['unable to check status of %s: %s' % (name, e)]
        return
    assert isinstance(info, PointInfo)
    if info.last_success is None:
        values['return_code'] = 2
        values['return_text'] += ['no successful backup of %s' % name]
    else:
        now = datetime.datetime.now()
        out_of_date = collect_point.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            values['return_code'] = max(values['return_code'], 1)
            values['return_text'] += ['the last backup of %s is out of date: %s' % (name, info.last_success)]
    if info.last_state_valid is False:
        values['return_code'] = 2
        values['return_text'] += ['the last backup of %s has failed. %s' % (name, info.last_message)]


def check_backup_collect_points(values, collect_point, backup_point):
    assert isinstance(collect_point, CollectPoint)
    assert isinstance(backup_point, BackupPoint)
    name = '%s:%s' % (collect_point.name, backup_point.name)
    try:
        info = backup_point.get_info(collect_point)
    except ValueError as e:
        values['return_code'] = 2
        values['return_text'] += ['unable to check status of %s: %s' % (name, e)]
        return
    assert isinstance(info, PointInfo)
    if info.last_success is None:
        values['return_code'] = 2
        values['return_text'] += ['no successful backup of %s' % name]
    else:
        now = datetime.datetime.now()
        out_of_date = collect_point.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
        if out_of_date:
            values['return_code'] = max(values['return_code'], 1)
            values['return_text'] += ['the last backup of %s is out of date: %s' % (name, info.last_success)]
    if info.last_state_valid is False:
        values['return_code'] = 2
        values['return_text'] += ['the last backup of %s has failed. %s' % (name, info.last_message)]
