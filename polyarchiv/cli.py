# -*- coding: utf-8 -*-
"""Core shell application.
Parse arguments and logger, use translated strings.
"""
from __future__ import unicode_literals

import argparse
import functools
import logging
import logging.config
import math
import os
import re
import subprocess
import sys

from polyarchiv.check import check_collect_point, check_backup_collect_points
from polyarchiv.conf import Parameter
from polyarchiv.termcolor import cprint, YELLOW, CYAN, BOLD, GREEN, GREY, RED

__author__ = 'Matthieu Gallet'


def main(engines_file=None):
    """Main function, intended for use as command line executable.

    Returns:
      * :class:`int`: 0 in case of success, != 0 if something went wrong

    """
    path_components = sys.executable.split(os.path.sep)
    if sys.executable.startswith('/usr/'):
        path_components = ['', 'etc', 'polyarchiv']
    elif 'bin' in path_components:
        # noinspection PyTypeChecker
        path_components = path_components[:path_components.index('bin')] + ['etc', 'polyarchiv']
    else:
        path_components = ['config']

    log = {'version': 1, 'disable_existing_loggers': True,
           'formatters': {'color': {'()': 'logging.Formatter', 'format': "%(message)s"}},
           'handlers': {'stream': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'color'}},
           'loggers': {'polyarchiv': {'handlers': ['stream', ], 'level': 'ERROR', 'propagate': False}}}

    config_dir = os.path.sep.join(path_components)
    parser = argparse.ArgumentParser(description='backup data from multiple sources')
    parser.add_argument('-v', '--verbose', action='store_true', help='print more messages', default=False)
    parser.add_argument('-f', '--force', action='store_true', help='force backup if not out-of-date', default=False)
    parser.add_argument('-n', '--nrpe', action='store_true', help='Nagios-compatible output', default=False)
    parser.add_argument('-D', '--dry', action='store_true', help='dry mode: do not execute commands', default=False)
    parser.add_argument('--show-commands', action='store_true', help='display all bash executed commands',
                        default=False)
    parser.add_argument('--confirm-commands', action='store_true', help='ask the user to confirm each command',
                        default=False)
    parser.add_argument('--only-collect-points', nargs='+', help='limit to these collect point tags', default=[])
    parser.add_argument('--only-backup-points', nargs='+', help='limit to these backup point tags', default=[])
    parser.add_argument('--skip-collect', action='store_true', help='skip the collect step during a backup',
                        default=False)
    parser.add_argument('--skip-backup', action='store_true', help='skip the backup step during a backup',
                        default=False)
    parser.add_argument('--config', '-C', default=config_dir, help='config dir')
    parser.add_argument('command', help='backup|restore|config|plugins')
    args = parser.parse_args()
    command = args.command
    verbose = args.verbose
    if verbose:
        log['loggers']['polyarchiv']['level'] = 'DEBUG'
    elif args.nrpe:
        log['loggers']['polyarchiv']['level'] = 'CRITICAL'
    logging.config.dictConfig(log)
    return_code = 0
    if args.dry:
        cprint('dry mode is selected: no write operation will be performed', YELLOW)

    from polyarchiv.runner import Runner  # import it after the log configuration
    runner = Runner([args.config], engines_file=engines_file, command_display=args.show_commands,
                    command_confirm=args.confirm_commands, command_execute=not args.dry,
                    command_keep_output=verbose)
    if command == 'backup':
        if runner.load():
            collect_point_results, backup_point_results = runner.backup(only_collect_points=args.only_collect_points,
                                                                        only_backup_points=args.only_backup_points,
                                                                        force=args.force,
                                                                        skip_collect=args.skip_collect,
                                                                        skip_backup=args.skip_backup)
            collect_point_failures = ['collect_point:%s' % x for (x, y) in collect_point_results.items() if not y]
            backup_point_failures = ['collect_point:%s/backup_point:%s' % x for (x, y) in backup_point_results.items()
                                     if not y]
            if collect_point_failures or backup_point_failures:
                if args.nrpe:
                    cprint('CRITICAL - failed backups: %s ' % ' '.join(collect_point_failures + backup_point_failures))
                return_code = 2
            elif args.nrpe:
                cprint('OK - all backups are valid')
                return_code = 0
        else:
            if args.nrpe:
                cprint('CRITICAL - unable to load configuration')
            return_code = 1
    elif command == 'restore':
        if runner.load():
            runner.restore(args.only_collect_points, args.only_backup_points)
    elif command == 'config':
        cprint('configuration directory: %s (you can change it with -C /other/directory)' % args.config, YELLOW)
        if runner.load():
            if not verbose:
                cprint('you can display more info with --verbose', CYAN)
            from polyarchiv.show import show_collect_point, show_backup_collect_point, show_backup_point
            runner.apply_commands(collect_point_command=show_collect_point, backup_point_command=show_backup_point,
                                  collect_point_backup_point_command=show_backup_collect_point,
                                  only_collect_points=args.only_collect_points,
                                  only_backup_points=args.only_backup_points)
    elif command == 'check':
        if runner.load():
            from polyarchiv.show import show_collect_point, show_backup_collect_point, \
                show_backup_point
            values = {'return_text': [], 'return_code': 0}
            collect_point_command = functools.partial(check_collect_point, values)
            backup_point_command = functools.partial(check_backup_collect_points, values)
            runner.apply_commands(collect_point_command=collect_point_command,
                                  collect_point_backup_point_command=backup_point_command,
                                  only_collect_points=args.only_collect_points,
                                  only_backup_points=args.only_backup_points)
            return_code = values['return_code']
            msg = ', '.join(values['return_text'])
            if return_code == 0:
                msg = 'everything is valid'
        else:
            msg = 'Unable to load configuration'
            return_code = 2
        if args.nrpe:
            if return_code == 2:
                msg = 'CRITICAL - %s' % msg
            elif return_code == 1:
                msg = 'WARNING - %s' % msg
            elif return_code == 0:
                msg = 'OK - %s' % msg
            else:
                msg = 'UNKNOWN - %s' % msg
        cprint(msg)
    elif command == 'plugins':
        width = 80
        tput_cols = subprocess.check_output(['tput', 'cols']).decode().strip()
        if re.match('^\d+$', tput_cols):
            width = int(tput_cols)
        cprint('configuration directory: %s' % args.config, YELLOW)
        if not verbose:
            cprint('display available options for each engine with --verbose', CYAN)

        available_collect_point_engines, available_source_engines, available_backup_point_engines, \
            available_filter_engines = Runner.find_available_engines(engines_file)
        cprint('available collect point engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_collect_point_engines, verbose=verbose, width=width)
        cprint('available source engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_source_engines, verbose=verbose, width=width)
        cprint('available backup point engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_backup_point_engines, verbose=verbose, width=width)
        cprint('available filter engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_filter_engines, verbose=verbose, width=width)
        cprint('[*] this parameter can use variables. See the README (\'Replacement rules\' section)', RED)
        cprint('[**] this parameter can only use time/host-independent variables. See the README', RED)
    else:
        cprint('unknown command \'%s\'' % command, RED)
        cprint('available commands: backup|restore|config|plugins', YELLOW)
    return return_code


def display_classes(engines, verbose=False, width=80):
    """display plugins of a given category"""
    for name, engine_cls in engines.items():
        cprint('  * engine=%s' % name, BOLD, GREEN)
        if engine_cls.__doc__:
            cprint('    ' + engine_cls.__doc__.strip(), GREY, BOLD)

        if verbose:
            cprint('    options:', GREEN)
        # noinspection PyUnresolvedReferences
        for parameter in engine_cls.parameters:
            assert isinstance(parameter, Parameter)
            if parameter.common:
                continue
            elif parameter.help_str:
                txt = '%s: %s' % (parameter.option_name, parameter.help_str)
                lines = []
                w = width - 8
                for line in txt.splitlines():
                    lines += [line[w * i:w * (i + 1)] for i in range(int(math.ceil(len(line) / float(w))))]
                if verbose:
                    cprint('      - ' + ('\n        '.join(lines)), GREEN)
            else:
                if verbose:
                    cprint('      - %s' % parameter.option_name, GREEN)
        if verbose:
            cprint('    ' + '-' * (width - 4), GREEN)
