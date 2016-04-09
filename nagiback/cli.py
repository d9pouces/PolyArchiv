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
           'formatters': {'color': {'()': 'colorlog.ColoredFormatter', 'format': "%(log_color)s%(message)s%(reset)s"}},
           'handlers': {'stream': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'color'}},
           'loggers': {'nagiback': {'handlers': ['stream', ], 'level': 'ERROR', 'propagate': False}}}

    config_dir = os.path.sep.join(path_components)
    parser = argparse.ArgumentParser(description='Backup data from multiple sources')
    parser.add_argument('-v', '--verbose', action='store_true', help='print more messages', default=False)
    parser.add_argument('-n', '--nagios', action='store_true', help='Nagios-compatible output', default=False)
    parser.add_argument('--only-locals', nargs='+', help='limit to these local tags', default=[])
    parser.add_argument('--only-remotes', nargs='+', help='limit to these remote tags', default=[])
    parser.add_argument('--config', '-C', default=config_dir, help='config dir')
    parser.add_argument('command', help='backup|show|restore')
    args = parser.parse_args()
    command = args.command
    print(args)
    if args.verbose:
        log['loggers']['nagiback']['level'] = 'DEBUG'
    logging.config.dictConfig(log)
    logger = logging.getLogger('nagiback.cli')
    from nagiback.runner import Runner
    if command == 'backup':
        runner = Runner([args.config])
    elif command == 'restore':
        runner = Runner([args.config])
    elif command == 'show':
        logger.info('Configuration directory: %s' % args.config)
        runner = Runner([args.config])
        if not args.verbose:
            logger.error('Display more info with --verbose')
        runner.apply_commands(lambda x: logger.info('local repository %s selected' % x.name),
                              lambda x, y: logger.info('remote repository %s on local %s selected' % (y.name, x.name)),
                              only_locals=args.only_locals, only_remotes=args.only_remotes)
    return_code = 0  # 0 = success, != 0 = error
    # complete this function
    return return_code


if __name__ == '__main__':
    import doctest

    doctest.testmod()
