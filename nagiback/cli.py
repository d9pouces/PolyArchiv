# -*- coding: utf-8 -*-
"""Core shell application.
Parse arguments and logger, use translated strings.
"""
from __future__ import unicode_literals

import argparse
import os
import sys
from nagiback.runner import Runner

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
        path_components = path_components[:path_components.index('bin')] + ['etc']
    else:
        path_components = ['config']
    config_dir = os.path.join(*path_components)
    parser = argparse.ArgumentParser(description='Backup data from multiple sources')
    parser.add_argument('-v', '--verbose', action='store_true', help='print more messages', default=False)
    parser.add_argument('-n', '--nagios', action='store_true', help='Nagios-compatible output', default=False)
    parser.add_argument('--only-locals', nargs='+', help='limit to these local tags')
    parser.add_argument('--only-remotes', nargs='+', help='limit to these remote tags')
    parser.add_argument('--config', default=config_dir, help='config dir')
    parser.add_argument('command', help='backup|show|restore')
    args = parser.parse_args()
    print(args)
    runner = Runner(args.config)
    command = args.command
    if command == 'backup':
        pass
    elif command == 'restore':
        pass
    elif command == 'show':
        pass
    return_code = 0  # 0 = success, != 0 = error
    # complete this function
    return return_code


if __name__ == '__main__':
    import doctest
    doctest.testmod()
