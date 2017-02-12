# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import

import datetime

from polyarchiv.backup_points import BackupPoint
from polyarchiv.collect_points import CollectPoint
from polyarchiv.filters import FileFilter
from polyarchiv.hooks import Hook
from polyarchiv.points import PointInfo
from polyarchiv.runner import Runner
from polyarchiv.sources import Source


__author__ = 'Matthieu Gallet'


# noinspection PyMethodMayBeStatic
class Visitor(object):
    """All these methods are called in this order."""

    def visit_runner(self, runner):
        """Called on the runner"""
        pass

    def visit_backup_points(self, runner, backup_points):
        """Called with all selected backup points"""
        pass

    def visit_backup_point(self, runner, backup_point):
        """Called on each backup point"""
        pass

    def visit_backup_point_collect_points(self, runner, backup_point, collect_points):
        """For each selected backup point, called all collect points associated to this backup point """
        pass

    def visit_collect_points(self, runner, collect_points):
        """Called with all selected collect points"""
        pass

    def visit_collect_point(self, runner, collect_point):
        """Called on each selected collect point"""
        pass

    def visit_backup_points_collect_point(self, runner, backup_points, collect_point):
        """For each selected collect point, called all backup points associated to this collect point"""
        pass

    def visit_backup_point_collect_point(self, runner, backup_point, collect_point):
        """Applied to all valid couples (backup point, collect point)"""
        pass


class ConfigVisitor(Visitor):
    def __init__(self, engines_file=None):
        self.engines_file = engines_file

    def visit_collect_point(self, runner, collect_point):
        available_collect_point_engines, available_source_engines, __, available_filter_engines, available_hook_engines\
            = Runner.find_available_engines(self.engines_file)

        # ##############################################################################################################
        assert isinstance(collect_point, CollectPoint)
        runner.print_command('collect point %s selected' % collect_point.name)
        if collect_point.__class__ in available_collect_point_engines:
            engine = available_collect_point_engines[collect_point.__class__]
        else:
            engine = '%s.%s' % (collect_point.__class__.__module__, collect_point.__class__.__name__)
        runner.print_info('engine: %s' % engine)
        if collect_point.__doc__:
            runner.print_command_output(collect_point.__doc__)
        # ##############################################################################################################
        for source in collect_point.sources:
            assert isinstance(source, Source)
            runner.print_command('  * source %s added to %s' % (source.name, collect_point.name))
            if source.__class__ in available_source_engines:
                engine = available_source_engines[source.__class__]
            else:
                engine = '%s.%s' % (source.__class__.__module__, source.__class__.__name__)
            runner.print_info('engine: %s' % engine)
            if source.__doc__:
                runner.print_command_output(source.__doc__)
        # ##############################################################################################################
        for filter_ in collect_point.filters:
            assert isinstance(filter_, FileFilter)
            runner.print_command('  * filter %s added to %s' % (filter_.name, collect_point.name))
            if filter_.__class__ in available_filter_engines:
                engine = available_filter_engines[filter_.__class__]
            else:
                engine = '%s.%s' % (filter_.__class__.__module__, filter_.__class__.__name__)
            runner.print_info('engine: %s' % engine)
            if filter_.__doc__:
                runner.print_command_output(filter_.__doc__)
        # ##############################################################################################################
        for hook in collect_point.hooks:
            assert isinstance(hook, Hook)
            runner.print_command('  * hook %s added to %s' % (hook.name, collect_point.name))
            if hook.__class__ in available_hook_engines:
                engine = available_hook_engines[hook.__class__]
            else:
                engine = '%s.%s' % (hook.__class__.__module__, hook.__class__.__name__)
            runner.print_info('engine: %s' % engine)
            if hook.__doc__:
                runner.print_command_output(hook.__doc__)
        # ##############################################################################################################
        try:
            info = collect_point.get_info()
        except ValueError as e:
            runner.print_error('Unable to retrieve more information from the collect point: %s' % e)
            return
        assert isinstance(info, PointInfo)
        if info.last_success is None:
            runner.print_error('No successful local collect')
        else:
            now = datetime.datetime.now()
            out_of_date = collect_point.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
            if out_of_date:
                runner.print_command('Last local collect is out of date: %s' % info.last_success)
            else:
                runner.print_success('Last local collect is recent enough: %s' % info.last_success)
        if info.last_state_valid is False:
            runner.print_error('The last backup has failed. %s' % info.last_message)

    def visit_backup_point(self, runner, backup_point):
        __, __, available_backup_point_engines, available_filter_engines, available_hook_engines = \
            Runner.find_available_engines(self.engines_file)
        assert isinstance(backup_point, BackupPoint)
        runner.print_info('backup point %s selected' % backup_point.name)
        if backup_point.__class__ in available_backup_point_engines:
            engine = available_backup_point_engines[backup_point.__class__]
        else:
            engine = '%s.%s' % (backup_point.__class__.__module__, backup_point.__class__.__name__)
        runner.print_command_output('engine: %s' % engine)
        if backup_point.__doc__:
            runner.print_command_output(backup_point.__doc__)
        # ##############################################################################################################
        for filter_ in backup_point.filters:
            assert isinstance(filter_, FileFilter)
            runner.print_command('  * filter %s added to %s' % (filter_.name, backup_point.name))
            if filter_.__class__ in available_filter_engines:
                engine = available_filter_engines[filter_.__class__]
            else:
                engine = '%s.%s' % (filter_.__class__.__module__, filter_.__class__.__name__)
            runner.print_info('engine: %s' % engine)
            if filter_.__doc__:
                runner.print_command_output(filter_.__doc__)
        # ##############################################################################################################
        for hook in backup_point.hooks:
            assert isinstance(hook, Hook)
            runner.print_command('  * hook %s added to %s' % (hook.name, backup_point.name))
            if hook.__class__ in available_hook_engines:
                engine = available_hook_engines[hook.__class__]
            else:
                engine = '%s.%s' % (hook.__class__.__module__, hook.__class__.__name__)
            runner.print_info('engine: %s' % engine)
            if hook.__doc__:
                runner.print_command_output(hook.__doc__)

    def visit_backup_point_collect_point(self, runner, backup_point, collect_point):
        assert isinstance(collect_point, CollectPoint)
        assert isinstance(backup_point, BackupPoint)
        runner.print_info('  * backup point %s selected on collect point %s' % (backup_point.name, collect_point.name))
        try:
            info = backup_point.get_info(collect_point)
        except ValueError as e:
            runner.print_error('Unable to retrieve more information from the backup point: %s' % e)
            return
        assert isinstance(info, PointInfo)
        if info.last_success is None:
            runner.print_error('No successful remote backup for %s' % backup_point.name)
        else:
            now = datetime.datetime.now()
            out_of_date = collect_point.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
            if out_of_date:
                runner.print_command('Last local collect is out of date on %s: %s' %
                                     (backup_point.name, info.last_success))
            else:
                runner.print_success('Last local collect is recent enough on %s: %s' %
                                     (backup_point.name, info.last_success))
        if info.last_state_valid is False:
            runner.print_error('The last collect has failed on %s. %s' % (backup_point.name, info.last_message))

    def visit_backup_point_collect_points(self, runner, backup_point, collect_points):
        assert isinstance(backup_point, BackupPoint)
        for check in backup_point.checks:
            check(runner, backup_point, collect_points)

    def visit_backup_points_collect_point(self, runner, backup_points, collect_point):
        assert isinstance(collect_point, CollectPoint)
        for check in collect_point.checks:
            check(runner, collect_point, backup_points)


class CheckVisitor(Visitor):
    def __init__(self):
        self.return_code = 0
        self.errors = []
        self.warnings = []
        self.infos = []

    def visit_collect_point(self, runner, collect_point_):
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

    def visit_backup_point_collect_point(self, runner, backup_point, collect_point):
        assert isinstance(collect_point, CollectPoint)
        assert isinstance(backup_point, BackupPoint)
        name = '%s:%s' % (collect_point.name, backup_point.name)
        try:
            info = backup_point.get_info(collect_point)
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
            out_of_date = collect_point.check_out_of_date_backup(current_time=now, previous_time=info.last_success)
            if out_of_date:
                self.return_code = max(self.return_code, 1)
                self.errors += ['the last backup of %s is out of date: %s' % (name, info.last_success)]
        if info.last_state_valid is False:
            self.return_code = 2
            self.errors += ['the last backup of %s has failed. %s' % (name, info.last_message)]
