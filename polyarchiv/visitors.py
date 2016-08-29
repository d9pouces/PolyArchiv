# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import

import datetime

from polyarchiv.backup_points import BackupPoint
from polyarchiv.collect_points import CollectPoint
from polyarchiv.config_show import show_collect_point, show_backup_point, show_backup_collect_point
from polyarchiv.points import PointInfo

__author__ = 'Matthieu Gallet'


class Visitor(object):

    def runner(self, runner):
        pass

    def backup_point(self, runner, backup_point):
        pass

    def collect_point(self, runner, collect_point):
        pass

    def backup_points(self, runner, backup_points):
        pass

    def collect_points(self, runner, collect_points):
        pass

    def backup_point_collect_point(self, runner, backup_point, collect_point):
        pass

    def backup_points_collect_point(self, runner, backup_points, collect_point):
        pass

    def backup_point_collect_points(self, runner, backup_point, collect_points):
        pass


class ConfigVisitor(Visitor):
    def __init__(self, engines_file=None):
        self.engines_file = engines_file

    def collect_point(self, runner, collect_point):
        show_collect_point(collect_point, engines_file=self.engines_file)

    def backup_point(self, runner, backup_point):
        show_backup_point(backup_point, engines_file=self.engines_file)

    def backup_point_collect_point(self, runner, backup_point, collect_point):
        show_backup_collect_point(collect_point, backup_point)


class CheckVisitor(Visitor):
    def __init__(self):
        self.return_code = 0
        self.errors = []
        self.warnings = []
        self.infos = []

    def collect_point(self, runner, collect_point_):
        assert isinstance(collect_point_, CollectPoint)
        name = collect_point_.name
        try:
            info = collect_point_.get_info()
        except ValueError as e:
            self.return_code = 2
            self.errors += ['unable to check status of %s: %s' % (name, e)]
            return
        assert isinstance(info, PointInfo)
        if info.last_success is None:
            self.return_code = 2
            self.errors += ['no successful backup of %s' % name]
        else:
            now = datetime.datetime.now()
            out_of_date = collect_point_.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
            if out_of_date:
                self.return_code = max(self.return_code, 1)
                self.errors += ['the last backup of %s is out of date: %s' % (name, info.last_success)]
        if info.last_state_valid is False:
            self.return_code = 2
            self.errors += ['the last backup of %s has failed. %s' % (name, info.last_message)]

    def backup_point_collect_point(self, runner, backup_point_, collect_point_):
        assert isinstance(collect_point_, CollectPoint)
        assert isinstance(backup_point_, BackupPoint)
        name = '%s:%s' % (collect_point_.name, backup_point_.name)
        try:
            info = backup_point_.get_info(collect_point_)
        except ValueError as e:
            self.return_code = 2
            self.errors += ['unable to check status of %s: %s' % (name, e)]
            return
        assert isinstance(info, PointInfo)
        if info.last_success is None:
            self.return_code = 2
            self.errors += ['no successful backup of %s' % name]
        else:
            now = datetime.datetime.now()
            out_of_date = collect_point_.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
            if out_of_date:
                self.return_code = max(self.return_code, 1)
                self.errors += ['the last backup of %s is out of date: %s' % (name, info.last_success)]
        if info.last_state_valid is False:
            self.return_code = 2
            self.errors += ['the last backup of %s has failed. %s' % (name, info.last_message)]
