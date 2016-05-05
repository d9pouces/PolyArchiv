# -*- coding: utf-8 -*-
"""Core shell application.
Parse arguments and logger, use translated strings.
"""
from __future__ import unicode_literals

import argparse
import logging
import logging.config
import math
import os
import sys

from pkg_resources import iter_entry_points

from polyarchiv.conf import Parameter
from polyarchiv.termcolor import cprint, YELLOW, CYAN, BOLD, GREEN

__author__ = 'mgallet'


def main():
    """Main function, intended for use as command line executable.

    Returns:
      * :class:`int`: 0 in case of success, != 0 if something went wrong

    """
    path_components = sys.executable.split(os.path.sep)
    if sys.executable.startswith('/usr/'):
        path_components = ['', 'etc']
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
    parser.add_argument('--show-commands', action='store_true', help='display all bash executed commands', default=False)
    parser.add_argument('--confirm-commands', action='store_true', help='ask the user to confirm each command', default=False)
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

    from polyarchiv.runner import Runner  # import it after the log configuration
    if command == 'backup':
        runner = Runner([args.config], command_display=args.show_commands, command_confirm=args.confirm_commands,
                        command_execute=not args.dry, command_keep_output=verbose)
        local_results, remote_results = runner.backup(only_locals=args.only_locals, only_remotes=args.only_remotes,
                                                      force=args.force)
        local_failures = ['local:%s' % x for (x, y) in local_results.items() if not y]
        remote_failures = ['local:%s/remote:%s' % x for (x, y) in remote_results.items() if not y]
        if local_failures or remote_failures:
            if args.nrpe:
                print('CRITICAL - failed backups: %s ' % ' '.join(local_failures + remote_failures))
            return_code = 2
        elif args.nrpe:
            print('OK - all backups are valid')
            return_code = 0
    elif command == 'restore':
        runner = Runner([args.config], command_display=args.show_commands, command_confirm=args.confirm_commands,
                        command_execute=not args.dry, command_keep_output=verbose)
        runner.restore(args.only_locals, args.only_remotes)
    elif command == 'config':
        cprint('configuration directory: %s (you can change it with -C /other/directory)' % args.config, YELLOW)
        runner = Runner([args.config], command_display=args.show_commands, command_confirm=args.confirm_commands,
                        command_execute=not args.dry, command_keep_output=verbose)
        if not verbose:
            cprint('display more info with --verbose', CYAN)
        from polyarchiv.show import show_local_repository, show_remote_local_repository, show_remote_repository
        runner.apply_commands(local_command=show_local_repository, remote_command=show_remote_repository,
                              local_remote_command=show_remote_local_repository,
                              only_locals=args.only_locals, only_remotes=args.only_remotes)
    elif command == 'plugins':
        cprint('configuration directory: %s' % args.config, YELLOW)
        if not verbose:
            cprint('display available options for each engine with --verbose', CYAN)

        cprint('available built-in local repository engines:', YELLOW)
        # noinspection PyTypeChecker
        display_classes('polyarchiv.locals', verbose=verbose)
        cprint('available built-in source engines:', YELLOW)
        # noinspection PyTypeChecker
        display_classes('polyarchiv.sources', verbose=verbose)
        cprint('available built-in remote repository engines:', YELLOW)
        # noinspection PyTypeChecker
        display_classes('polyarchiv.remotes', verbose=verbose)
    return return_code


def display_classes(plugin_category, verbose=False):
    """display plugins of a given category"""
    for entry_point in iter_entry_points(plugin_category):
        v = entry_point.load()
        cprint('  * engine=%s.%s' % (v.__module__, v.__name__), BOLD, GREEN)
        if verbose:
            cprint('    options:', GREEN)
        # noinspection PyUnresolvedReferences
        for parameter in v.parameters:
            assert isinstance(parameter, Parameter)
            if parameter.help_str:
                lines = []
                for line in parameter.help_str.splitlines():
                    lines += [line[70 * i:70 * (i + 1)] for i in range(int(math.ceil(len(line) / 70.)))]
                if verbose:
                    cprint('      - %s: %s' % (parameter.option_name, '\n        '.join(lines)), GREEN)
            else:
                if verbose:
                    cprint('      - %s' % parameter.option_name, GREEN)
        if verbose:
            cprint('    -----------------------------------------------------------------------------', GREEN)
