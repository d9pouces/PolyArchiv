# -*- coding: utf-8 -*-
"""Core shell application.
Parse arguments and logger, use translated strings.
"""
from __future__ import unicode_literals

import argparse
import math
import os
import re
import subprocess
import sys

from polyarchiv.conf import Parameter
from polyarchiv.termcolor import cprint, YELLOW, CYAN, BOLD, GREEN, GREY, RED
from polyarchiv.visitors import ConfigVisitor, CheckVisitor

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

    config_dir = os.path.sep.join(path_components)
    parser = argparse.ArgumentParser(description='backup data from multiple sources')
    parser.add_argument('-v', '--verbose', action='store_true', help='equivalent to --verbosity=3', default=False)
    parser.add_argument('-q', '--quiet', action='store_true', help='equivalent to --verbosity=0', default=False)
    parser.add_argument('--verbosity', type=int, help='Level of verbosity.\n'
                                                      '0: as quiet as possible (only errors are displayed)\n'
                                                      '1: executed commands are displayed\n'
                                                      '2: result of commands are displayed\n'
                                                      '3: full command output', default=None)
    parser.add_argument('--log-file', default=None, help='log file')
    parser.add_argument('-f', '--force', action='store_true', help='force backup if not out-of-date', default=False)
    parser.add_argument('-n', '--nrpe', action='store_true', help='Nagios-compatible output', default=False)
    parser.add_argument('-D', '--dry', action='store_true', help='dry mode: do not execute commands', default=False)
    parser.add_argument('--show-commands', action='store_true', help='equivalent to --verbosity=1',
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
    parser.add_argument('command', choices=('backup', 'restore', 'config', 'plugins', 'check'))
    args = parser.parse_args()
    command = args.command
    verbosity = 1
    if args.verbosity is not None:
        verbosity = args.verbosity
    elif args.verbose:
        verbosity = 3
    elif args.show_commands:
        verbosity = 1
    elif args.quiet:
        verbosity = 0

    return_code = 0
    if args.dry:
        cprint('dry mode is selected: no write operation will be performed', YELLOW)

    from polyarchiv.runner import Runner  # import it after the log configuration
    runner = Runner([args.config], engines_file=engines_file, verbosity=verbosity,
                    command_confirm=args.confirm_commands, command_execute=not args.dry, log_file=args.log_file)
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
            if verbosity == 1:
                cprint('you can display more info with --verbose', CYAN)
            visitor = ConfigVisitor(engines_file=engines_file)
            runner.visit(visitor, only_collect_points=args.only_collect_points,
                         only_backup_points=args.only_backup_points)
    elif command == 'check':
        visitor = CheckVisitor()
        if runner.load():
            runner.visit(visitor, only_collect_points=args.only_collect_points,
                         only_backup_points=args.only_backup_points)
            return_code = visitor.return_code
            msg = ', '.join(visitor.errors)
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
        elif visitor.warnings:
            msg += '\n' + '\n'.join(visitor.warnings)
        cprint(msg)
    elif command == 'plugins':
        width = 80
        tput_cols = subprocess.check_output(['tput', 'cols']).decode().strip()
        if re.match('^\d+$', tput_cols):
            width = int(tput_cols)
        cprint('configuration directory: %s' % args.config, YELLOW)
        if verbosity == 1:
            cprint('display available options for each engine with --verbose', CYAN)

        available_collect_point_engines, available_source_engines, available_backup_point_engines, \
            available_filter_engines, available_hook_engines = Runner.find_available_engines(engines_file)
        cprint('available collect point engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_collect_point_engines, verbosity=verbosity, width=width)
        cprint('available source engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_source_engines, verbosity=verbosity, width=width)
        cprint('available backup point engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_backup_point_engines, verbosity=verbosity, width=width)
        cprint('available filter engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_filter_engines, verbosity=verbosity, width=width)
        cprint('available hook engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes(available_hook_engines, verbosity=verbosity, width=width)
        cprint('[*] this parameter can use variables. See the README (\'Replacement rules\' section)', RED)
        cprint('[**] this parameter can only use time/host-independent variables. See the README', RED)
    else:
        cprint('unknown command \'%s\'' % command, RED)
        cprint('available commands: backup|restore|config|plugins', YELLOW)
    return return_code


def display_classes(engines, verbosity=1, width=80):
    """display plugins of a given category"""
    for name, engine_cls in engines.items():
        cprint('  * engine=%s' % name, BOLD, GREEN)
        if engine_cls.__doc__:
            cprint('    ' + engine_cls.__doc__.strip(), GREY, BOLD)

        if verbosity >= 2:
            cprint('    options:', GREEN)
        # noinspection PyUnresolvedReferences
        for parameter in engine_cls.parameters:
            assert isinstance(parameter, Parameter)
            if parameter.help_str:
                txt = '%s: %s' % (parameter.option_name, parameter.help_str)
                lines = []
                w = width - 8
                for line in txt.splitlines():
                    lines += [line[w * i:w * (i + 1)] for i in range(int(math.ceil(len(line) / float(w))))]
                if verbosity >= 2:
                    cprint('      - ' + ('\n        '.join(lines)), GREEN)
            else:
                if verbosity >= 2:
                    cprint('      - %s' % parameter.option_name, GREEN)
        if verbosity >= 2:
            cprint('    ' + '-' * (width - 4), GREEN)
