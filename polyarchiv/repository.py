# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import datetime
import json
import logging
import os
import pipes
import subprocess

from polyarchiv.conf import Parameter, check_executable
from polyarchiv.termcolor import cprint, YELLOW
from polyarchiv.utils import get_is_time_elapsed, text_type, get_input_text

__author__ = 'Matthieu Gallet'
logger = logging.getLogger('polyarchiv')


class ParameterizedObject(object):
    parameters = []

    def __init__(self, name, command_display=True, command_confirm=False, command_execute=True,
                 command_keep_output=False):
        self.name = name
        self.command_display = command_display  # display each command before running it
        self.command_confirm = command_confirm  # ask the user to confirm each command
        self.command_execute = command_execute  # actually run commands (if False: ‘dry’ mode)
        self.command_keep_output = command_keep_output  # display all command outputs on stderr/stdout

    def can_execute_command(self, text):
        """Return False if dry mode is activated or if the command is not validated by the user.
         Return True otherwise.
         Display the command if required.
        """
        def smart_quote(y):
            if y in ('>', '<', '2>'):
                return y
            return pipes.quote(y)
        if isinstance(text, list):
            text = ' '.join([smart_quote(x) for x in text])
        result = '-'
        if text:
            if self.command_confirm:
                while result not in ('', 'y', 'n'):
                    result = get_input_text('%s [Y]/n\n' % text).lower()
            elif self.command_display:
                cprint(text, YELLOW)
        return result != 'n' and self.command_execute

    def execute_command(self, cmd, ignore_errors=False, cwd=None, stderr=None, stdout=None, stdin=None, env=None,
                        error_str=None):
        check_executable(cmd[0])
        return_code = 0
        cmd_text = [x for x in cmd]
        # noinspection PyTypeChecker
        if hasattr(stdin, 'name') and stdin.name:
            cmd_text += ['<',  stdin.name]
        # noinspection PyTypeChecker
        if hasattr(stdout, 'name') and stdout.name:
            cmd_text += ['>',  stdout.name]
        # noinspection PyTypeChecker
        if hasattr(stderr, 'name') and stderr.name:
            cmd_text += ['2>',  stderr.name]
        if env and self.command_display:
            for k, v in env.items():
                cprint('%s=%s' % (k, v), YELLOW)
        if cwd:
            self.can_execute_command(['cd', cwd])
        if self.can_execute_command(cmd_text):
            p = subprocess.Popen(cmd, stdin=stdin, stderr=stderr or self.stderr, stdout=stdout or self.stdout,
                                 cwd=cwd, env=env)
            p.communicate()
            return_code = p.returncode
            if return_code != 0 and error_str:
                logger.error(error_str)
            if return_code != 0 and not ignore_errors:
                raise subprocess.CalledProcessError(return_code, cmd[0])
        return return_code

    @property
    def stderr(self):
        # noinspection PyTypeChecker
        return open(os.devnull, 'wb') if not self.command_keep_output else None

    @property
    def stdout(self):
        # noinspection PyTypeChecker
        return open(os.devnull, 'wb') if not self.command_keep_output else None

    def ensure_dir(self, dirname, parent=False):
        """ensure that `dirname` exists and is a directory.

        :param dirname:
        :param parent: only check for the parent directory of `dirname`
        :return:
        """
        if parent:
            dirname = os.path.dirname(dirname)
        if os.path.exists(dirname) and not os.path.isdir(dirname):
            raise ValueError('%s exists but is not a directory' % dirname)
        elif os.path.isdir(dirname):
            return
        if self.can_execute_command(['mkdir', '-p', dirname]):
            try:
                os.makedirs(dirname)
            except OSError:
                raise ValueError('Unable to create the %s directory' % dirname)


class RepositoryInfo(object):
    def __init__(self, last_state_valid=None, last_success=None, last_fail=None, success_count=0, fail_count=0,
                 total_size=0, last_message=''):
        self.last_state_valid = last_state_valid  # None, True, False
        self.last_success = last_success  # expected to be filled by datetime.datetime.now()
        self.last_fail = last_fail  # expected to be filled by datetime.datetime.now()
        self.success_count = success_count  # number of successful backups
        self.fail_count = fail_count  # number of failed backups
        self.total_size = total_size  # total size (in bytes) of the backup
        self.last_message = last_message  # should be "ok" for a success, or an informative message on error

    @property
    def last(self):
        """Return the date of the last stored event (either success or fail), or None if no event is registered"""
        if self.last_fail is None and self.last_success is None:
            return None
        elif self.last_success is None:
            return self.last_fail
        elif self.last_fail is None:
            return self.last_success
        elif self.last_fail < self.last_success:
            return self.last_success
        return self.last_fail

    def to_dict(self):
        # noinspection PyTypeChecker
        result = {x: getattr(self, x) for x in ('last_state_valid', 'success_count', 'fail_count', 'total_size',
                                                'last_message')}
        result['last_success'] = self.datetime_to_str(self.last_success)
        result['last_fail'] = self.datetime_to_str(self.last_fail)
        return result

    @classmethod
    def from_dict(cls, data):
        kwargs = {}
        for k in 'success_count', 'fail_count', 'total_size':
            kwargs[k] = data.get(k, 0)
            assert isinstance(kwargs[k], int)
        kwargs['last_message'] = data.get('last_message', '')
        assert isinstance(kwargs['last_message'], text_type)
        for k in ('last_state_valid', ):
            kwargs[k] = data.get(k)
            assert kwargs[k] is None or isinstance(kwargs[k], bool)
        if data['last_fail']:
            kwargs['last_fail'] = cls.datetime_from_str(data['last_fail'])
        if data['last_success']:
            kwargs['last_success'] = cls.datetime_from_str(data['last_success'])
        return RepositoryInfo(**kwargs)

    @staticmethod
    def datetime_to_str(value=None):
        if value is None:
            return None
        # noinspection PyUnresolvedReferences
        return value.strftime('%Y-%m-%dT%H:%M:%S')

    @staticmethod
    def datetime_from_str(value=None):
        if value is None:
            return None
        # noinspection PyTypeChecker
        return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')

    def to_str(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_str(cls, text):
        data = json.loads(text)
        return cls.from_dict(data)

    def __le__(self, other):
        assert isinstance(other, RepositoryInfo)
        self_last = self.last
        other_last = other.last
        if self_last is None:
            return True
        elif other_last is None:
            return False
        return self_last <= other_last

    def __lt__(self, other):
        assert isinstance(other, RepositoryInfo)
        self_last = self.last
        other_last = other.last
        if self_last is None and other_last is None:
            return False
        elif self_last is None:
            return True
        elif other_last is None:
            return False
        return self_last < other_last

    def __ge__(self, other):
        assert isinstance(other, RepositoryInfo)
        self_last = self.last
        other_last = other.last
        if self_last is None:
            return other_last is None
        elif other_last is None:
            return True
        return self_last >= other_last

    def __gt__(self, other):
        assert isinstance(other, RepositoryInfo)
        self_last = self.last
        other_last = other.last
        if self_last is None and other_last is None:
            return False
        elif self_last is None:
            return False
        elif other_last is None:
            return True
        return self_last > other_last

    def __eq__(self, other):
        assert isinstance(other, RepositoryInfo)
        return self.last == other.last

    def __ne__(self, other):
        assert isinstance(other, RepositoryInfo)
        return self.last != other.last


class Repository(ParameterizedObject):
    parameters = ParameterizedObject.parameters + [
        Parameter('check_out_of_date_backup', 'frequency', converter=get_is_time_elapsed,
                  help_str='frequency of backup operations. Can be an integer (number of seconds),\n'
                           '"monthly:d" (at least the d-th day of each month, d = 0..28),\n'
                           '"weekly:d" (the d-th day of each week, d = 0..6),\n'
                           '"weekly" or "daily" (once a week or once a day),\n'
                           '"daily:h" (the h-th hour of each day, h = 0..23)'),
    ]

    def __init__(self, name, check_out_of_date_backup=None, **kwargs):
        super(Repository, self).__init__(name, **kwargs)
        self.check_out_of_date_backup = check_out_of_date_backup or get_is_time_elapsed(None)
