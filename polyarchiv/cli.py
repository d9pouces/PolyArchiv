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
import sys

import subprocess
from pkg_resources import iter_entry_points

from polyarchiv.check import check_local_repository, check_remote_local_repository
from polyarchiv.conf import Parameter
from polyarchiv.termcolor import cprint, YELLOW, CYAN, BOLD, GREEN, GREY, RED

__author__ = 'mgallet'


def main():
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
    parser.add_argument('--only-locals', nargs='+', help='limit to these local tags', default=[])
    parser.add_argument('--only-remotes', nargs='+', help='limit to these remote tags', default=[])
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
    if command == 'backup':
        runner = Runner([args.config], command_display=args.show_commands, command_confirm=args.confirm_commands,
                        command_execute=not args.dry, command_keep_output=verbose)
        if runner.load():
            local_results, remote_results = runner.backup(only_locals=args.only_locals, only_remotes=args.only_remotes,
                                                          force=args.force)
            local_failures = ['local:%s' % x for (x, y) in local_results.items() if not y]
            remote_failures = ['local:%s/remote:%s' % x for (x, y) in remote_results.items() if not y]
            if local_failures or remote_failures:
                if args.nrpe:
                    cprint('CRITICAL - failed backups: %s ' % ' '.join(local_failures + remote_failures))
                return_code = 2
            elif args.nrpe:
                cprint('OK - all backups are valid')
                return_code = 0
        else:
            if args.nrpe:
                cprint('CRITICAL - unable to load configuration')
            return_code = 1
    elif command == 'restore':
        runner = Runner([args.config], command_display=args.show_commands, command_confirm=args.confirm_commands,
                        command_execute=not args.dry, command_keep_output=verbose)
        if runner.load():
            runner.restore(args.only_locals, args.only_remotes)
    elif command == 'config':
        cprint('configuration directory: %s (you can change it with -C /other/directory)' % args.config, YELLOW)
        runner = Runner([args.config], command_display=args.show_commands, command_confirm=args.confirm_commands,
                        command_execute=not args.dry, command_keep_output=verbose)
        if runner.load():
            if not verbose:
                cprint('you can display more info with --verbose', CYAN)
            from polyarchiv.show import show_local_repository, show_remote_local_repository, show_remote_repository
            runner.apply_commands(local_command=show_local_repository, remote_command=show_remote_repository,
                                  local_remote_command=show_remote_local_repository,
                                  only_locals=args.only_locals, only_remotes=args.only_remotes)
    elif command == 'check':
        runner = Runner([args.config], command_display=args.show_commands,
                        command_confirm=args.confirm_commands,
                        command_execute=not args.dry, command_keep_output=verbose)
        if runner.load():
            from polyarchiv.show import show_local_repository, show_remote_local_repository, \
                show_remote_repository
            values = {'return_text': [], 'return_code': 0}
            local_command = functools.partial(check_local_repository, values)
            remote_command = functools.partial(check_remote_local_repository, values)
            runner.apply_commands(local_command=local_command, local_remote_command=remote_command,
                                  only_locals=args.only_locals, only_remotes=args.only_remotes)
            return_code = values['return_code']
            msg = ', '.join(values['return_text'])
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

        cprint('available local repository engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes('polyarchiv.locals', verbose=verbose, width=width)
        cprint('available source engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes('polyarchiv.sources', verbose=verbose, width=width)
        cprint('available remote repository engines:', YELLOW, BOLD)
        # noinspection PyTypeChecker
        display_classes('polyarchiv.remotes', verbose=verbose, width=width)
        cprint('[*] this parameter can use variables. See the README (\'Replacement rules\' section)', RED)
    else:
        cprint('unknown command \'%s\'' % command, RED)
        cprint('available commands: backup|restore|config|plugins', YELLOW)
    return return_code


def display_classes(plugin_category, verbose=False, width=80):
    """display plugins of a given category"""
    for entry_point in iter_entry_points(plugin_category):
        engine_cls = entry_point.load()
        cprint('  * engine=%s' % entry_point.name, BOLD, GREEN)
        if engine_cls.__doc__:
            cprint('    ' + engine_cls.__doc__.strip(), GREY, BOLD)

        if verbose:
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
                if verbose:
                    cprint('      - ' + ('\n        '.join(lines)), GREEN)
            else:
                if verbose:
                    cprint('      - %s' % parameter.option_name, GREEN)
        if verbose:
            cprint('    ' + '-' * (width - 4), GREEN)
