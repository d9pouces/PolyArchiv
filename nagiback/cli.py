# -*- coding: utf-8 -*-
"""Core shell application.
Parse arguments and logger, use translated strings.
"""
from __future__ import unicode_literals

import argparse
import logging
import logging.config
import os
import sys

from nagiback.conf import Parameter

__author__ = 'mgallet'


def main():
    """Main function, intended for use as command line executable.

    Args:
        None
    Returns:
      * :class:`int`: 0 in case of success, != 0 if something went wrong

    """
    path_components = sys.executable.split(os.path.sep)
    if sys.executable.startswith('/usr/'):
        path_components = ['', 'etc']
    elif 'bin' in path_components:
        # noinspection PyTypeChecker
        path_components = path_components[:path_components.index('bin')] + ['etc', 'nagiback']
    else:
        path_components = ['config']

    log = {'version': 1, 'disable_existing_loggers': True,
           'formatters': {'color': {'()': 'logging.Formatter', 'format': "%(message)s"}},
           'handlers': {'stream': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'color'}},
           'loggers': {'nagiback': {'handlers': ['stream', ], 'level': 'ERROR', 'propagate': False}}}

    config_dir = os.path.sep.join(path_components)
    parser = argparse.ArgumentParser(description='backup data from multiple sources')
    parser.add_argument('-v', '--verbose', action='store_true', help='print more messages', default=False)
    parser.add_argument('-f', '--force', action='store_true', help='force backup if not out-of-date', default=False)
    parser.add_argument('-n', '--nrpe', action='store_true', help='Nagios-compatible output', default=False)
    parser.add_argument('--only-locals', nargs='+', help='limit to these local tags', default=[])
    parser.add_argument('--only-remotes', nargs='+', help='limit to these remote tags', default=[])
    parser.add_argument('--config', '-C', default=config_dir, help='config dir')
    parser.add_argument('command', help='backup|restore|config|plugins')
    args = parser.parse_args()
    command = args.command
    if args.verbose:
        log['loggers']['nagiback']['level'] = 'DEBUG'
    elif args.nrpe:
        log['loggers']['nagiback']['level'] = 'CRITICAL'
    logging.config.dictConfig(log)
    logger = logging.getLogger('nagiback.cli')
    return_code = 0

    from nagiback.runner import Runner  # import after log configuration
    if command == 'backup':
        runner = Runner([args.config])
        local_results, remote_results = runner.backup(only_locals=args.only_locals, only_remotes=args.only_remotes,
                                                      force=args.force)
        local_failures = ['local:%s' % x for (x, y) in local_results.items() if not y]
        remote_failures = ['local:%s/remote:%s' % x for (x, y) in remote_results.items() if not y]
        if local_failures or remote_failures:
            if args.nrpe:
                print('CRITICAL - failed backups ' % ' '.join(local_failures + remote_failures))
            return_code = 2
        elif args.nrpe:
            print('OK - all backups are valid')
            return_code = 0
    elif command == 'restore':
        runner = Runner([args.config])
        runner.restore(args.only_locals, args.only_remotes)
    elif command == 'config':
        from nagiback.show import show_local_repository, show_remote_local_repository, show_remote_repository
        logger.info('configuration directory: %s (you can change it with -C /other/directory)' % args.config)
        runner = Runner([args.config])
        if not args.verbose:
            logger.error('display more info with --verbose')
        runner.apply_commands(local_command=show_local_repository, remote_command=show_remote_repository,
                              local_remote_command=show_remote_local_repository,
                              only_locals=args.only_locals, only_remotes=args.only_remotes)
    elif command == 'plugins':
        logger.info('configuration directory: %s' % args.config)
        if not args.verbose:
            logger.error('display available options for each engine with --verbose')
        from nagiback import sources, locals, remotes

        logger.error('available built-in local repository:')
        # noinspection PyTypeChecker
        display_classes(logger, locals, locals.LocalRepository)
        logger.error('available built-in sources:')
        # noinspection PyTypeChecker
        display_classes(logger, sources, sources.Source)
        logger.error('available built-in remote repository:')
        # noinspection PyTypeChecker
        display_classes(logger, remotes, remotes.RemoteRepository)

    return return_code


def display_classes(logger, module, cls):
    for k, v in module.__dict__.items():
        if not isinstance(v, type) or not issubclass(v, cls):
            continue
        logger.error('  * engine=%s.%s' % (v.__module__, v.__name__))
        logger.info('    options:')
        # noinspection PyUnresolvedReferences
        for parameter in v.parameters:
            assert isinstance(parameter, Parameter)
            if parameter.help_str:
                logger.info('      - %s: %s' % (parameter.option_name, parameter.help_str))
            else:
                logger.info('      - %s' % parameter.option_name)
        logger.info('    -----------------------------------------------------------------------------')
    logger.error('====================================================================================================')


if __name__ == '__main__':
    import doctest

    doctest.testmod()
