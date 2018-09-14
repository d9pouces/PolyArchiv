# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import datetime
import json
import os
import shutil
import subprocess
import tempfile

from polyarchiv.conf import Parameter, check_executable
from polyarchiv.termcolor import cprint, YELLOW, CYAN, GREEN, RED, BOLD, WHITE
from polyarchiv.utils import (
    get_is_time_elapsed,
    text_type,
    get_input_text,
    command_to_text,
)

__author__ = "Matthieu Gallet"


class Config(object):
    parameters = [
        Parameter(
            "rsync_executable",
            converter=check_executable,
            help_str='full path of the "rsync" executable',
        ),
        Parameter(
            "curl_executable",
            converter=check_executable,
            help_str='full path of the "curl" executable',
        ),
        Parameter(
            "restic_executable",
            converter=check_executable,
            help_str='full path of the "restic" executable',
        ),
        Parameter(
            "scp_executable",
            converter=check_executable,
            help_str='full path of the "scp" executable',
        ),
        Parameter(
            "ssh_executable",
            converter=check_executable,
            help_str='full path of the "ssh" executable',
        ),
        Parameter(
            "tar_executable",
            converter=check_executable,
            help_str='full path of the "tar" executable',
        ),
        Parameter(
            "svn_executable",
            converter=check_executable,
            help_str='full path of the "svn" executable',
        ),
    ]

    def __init__(
        self,
        command_display=True,
        command_confirm=False,
        command_execute=True,
        command_keep_output=False,
        rsync_executable="rsync",
        curl_executable="curl",
        git_executable="git",
        restic_executable="restic",
        scp_executable="scp",
        ssh_executable="ssh",
        tar_executable="tar",
        svn_executable="svn",
    ):
        self.command_display = command_display  # display each command before running it
        self.command_confirm = command_confirm  # ask the user to confirm each command
        self.command_execute = (
            command_execute
        )  # actually run commands (if False: 'dry' mode)
        self.command_keep_output = (
            command_keep_output
        )  # display all command outputs on stderr/stdout
        self.rsync_executable = rsync_executable
        self.curl_executable = curl_executable
        self.git_executable = git_executable
        self.restic_executable = restic_executable
        self.scp_executable = scp_executable
        self.ssh_executable = ssh_executable
        self.tar_executable = tar_executable
        self.svn_executable = svn_executable


class ParameterizedObject(object):
    parameters = []

    def __init__(
        self,
        name,
        verbosity=1,
        command_confirm=False,
        command_execute=True,
        config=None,
    ):
        self.name = name
        self.config = config
        self.verbosity = verbosity
        self.command_confirm = command_confirm  # ask the user to confirm each command
        self.command_execute = (
            command_execute
        )  # actually run commands (if False: 'dry' mode)
        self.output_temp_fd = (
            None
        )  # file descriptor used if a hook retains the stdout or the stderr
        self.variables = {"name": name}
        # self.variables["variable_name"] = "value"

    def print_message(
        self, text, display=True, color=None, bold=False, min_verbosity=1
    ):
        if self.verbosity < min_verbosity:
            return
        attrs = []
        if color:
            attrs = [color]
        if bold:
            attrs.append(BOLD)
        if display:
            cprint(text, *attrs)
        if self.output_temp_fd:
            self.output_temp_fd.write(text.encode("utf-8"))
            self.output_temp_fd.write(b"\n")

    def print_command(self, text, display=True):
        return self.print_message(
            command_to_text(text), color=YELLOW, display=display, min_verbosity=1
        )

    def print_error(self, text, display=True):
        return self.print_message(
            text, color=RED, display=display, min_verbosity=0, bold=True
        )

    def print_success(self, text, display=True):
        return self.print_message(text, color=GREEN, display=display, min_verbosity=1)

    def print_info(self, text, display=True):
        return self.print_message(text, color=CYAN, display=display, min_verbosity=2)

    def print_command_output(self, text, display=True):
        return self.print_message(text, color=WHITE, display=display, min_verbosity=3)

    def can_execute_command(self, text):
        """Return False if dry mode is activated or if the command is not validated by the user.
         Return True otherwise.
         Display the command if required.
        """
        text = command_to_text(text)
        result = "-"
        if text:
            if self.command_confirm:
                while result not in ("", "y", "n"):
                    result = get_input_text("%s [Y]/n\n" % text).lower()
            self.print_command(text, display=not self.command_confirm)
        return result != "n" and self.command_execute

    def execute_command(
        self,
        cmd,
        ignore_errors=False,
        cwd=None,
        stderr=None,
        stdout=None,
        stdin=None,
        env=None,
        error_str=None,
    ):
        check_executable(cmd[0])
        return_code = 0
        cmd_text = [x for x in cmd]
        # noinspection PyTypeChecker
        if hasattr(stdin, "name") and stdin.name:
            cmd_text += ["<", stdin.name]
        elif stdin is None:
            # noinspection PyTypeChecker
            stdin = open(os.devnull, "rb")
        # noinspection PyTypeChecker
        if hasattr(stdout, "name") and stdout.name:
            cmd_text += [">", stdout.name]
        # noinspection PyTypeChecker
        if hasattr(stderr, "name") and stderr.name:
            cmd_text += ["2>", stderr.name]
        if env:
            for k in sorted(env):
                self.print_command("%s=%s" % (k, env[k]))
        if cwd:
            self.ensure_dir(cwd, parent=False)
            self.print_command(["cd", cwd])
        if self.can_execute_command(cmd_text):
            p = subprocess.Popen(
                cmd,
                stdin=stdin,
                stderr=stderr or self.stderr,
                stdout=stdout or self.stdout,
                cwd=cwd,
                env=env,
            )
            stdout, stderr = p.communicate()
            return_code = p.returncode
            if return_code != 0 and error_str:
                self.print_error(error_str)
            if return_code != 0 and not ignore_errors:
                raise subprocess.CalledProcessError(return_code, cmd[0])
        else:
            stdout, stderr = None, None
        return return_code, stdout, stderr

    def ensure_dir(self, dirname, parent=False):
        """ensure that `dirname` exists and is a directory.

        :param dirname:
        :param parent: only check for the parent directory of `dirname`
        :return:
        """
        if parent:
            dirname = os.path.dirname(dirname)
        is_dir = os.path.isdir(dirname)
        if os.path.exists(dirname) and not is_dir:
            if self.can_execute_command(["rm", dirname]):
                os.remove(dirname)
            else:
                return False
        elif is_dir:
            return True
        if self.can_execute_command(["mkdir", "-p", dirname]):
            try:
                os.makedirs(dirname)
                return True
            except OSError:
                raise ValueError("Unable to create the %s directory" % dirname)
        return False

    def ensure_absent(self, path):
        if not os.path.exists(path):
            return True
        if not self.can_execute_command(["rm", "-rf", path]):
            return False
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError:
            raise ValueError("Unable to remove %s" % path)
        return True

    @property
    def stderr(self):
        if self.verbosity >= 3 and not self.output_temp_fd:
            return None
        elif self.output_temp_fd:
            return self.output_temp_fd
        self.output_temp_fd = open(os.devnull, "wb")
        return self.output_temp_fd

    @property
    def stdout(self):
        if self.verbosity >= 3 and not self.output_temp_fd:
            return None
        elif self.output_temp_fd:
            return self.output_temp_fd
        self.output_temp_fd = open(os.devnull, "wb")
        return self.output_temp_fd

    def format_value(self, value):
        if value is None:
            return None
        try:
            formatted_value = value.format(**self.variables)
        except KeyError as e:
            txt = text_type(e)[len("KeyError:") :]
            raise ValueError(
                "Unable to format '%s': variable %s is missing" % (value, txt)
            )
        return formatted_value


class PointInfo(object):
    def __init__(
        self,
        last_state_valid=None,
        last_success=None,
        last_fail=None,
        success_count=0,
        fail_count=0,
        total_size=0,
        last_message="",
        config_hash=None,
        variables=None,
        data=None,
    ):
        self.last_state_valid = last_state_valid  # None, True, False
        self.last_success = (
            last_success
        )  # expected to be filled by datetime.datetime.now()
        self.last_fail = last_fail  # expected to be filled by datetime.datetime.now()
        self.success_count = success_count  # number of successful backups
        self.fail_count = fail_count  # number of failed backups
        self.total_size = total_size  # total size (in bytes) of the backup
        self.last_message = (
            last_message
        )  # should be "ok" for a success, or an informative message on error
        self.config_hash = config_hash  # md5 hash of the config file
        self.variables = variables or {}  # variables["key"] = "value"
        self.data = (
            data
        )  # extra data, without any spec (its use depends of each kind of repository)

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
        result = {
            x: getattr(self, x)
            for x in (
                "last_state_valid",
                "success_count",
                "fail_count",
                "total_size",
                "last_message",
            )
        }
        result["last_success"] = self.datetime_to_str(self.last_success)
        result["last_fail"] = self.datetime_to_str(self.last_fail)
        result["config_hash"] = self.config_hash
        result["variables"] = self.variables
        result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data):
        kwargs = {}
        for k in "success_count", "fail_count", "total_size":
            kwargs[k] = data.get(k, 0)
            assert isinstance(kwargs[k], int)
        kwargs["last_message"] = data.get("last_message", "")
        assert isinstance(kwargs["last_message"], text_type)
        for k in ("last_state_valid",):
            kwargs[k] = data.get(k)
            assert kwargs[k] is None or isinstance(kwargs[k], bool)
        if data["last_fail"]:
            kwargs["last_fail"] = cls.datetime_from_str(data["last_fail"])
        if data["last_success"]:
            kwargs["last_success"] = cls.datetime_from_str(data["last_success"])
        if data.get("config_hash"):
            kwargs["config_hash"] = data["config_hash"]
        kwargs["variables"] = data.get("variables")
        kwargs["data"] = data.get("data")
        return PointInfo(**kwargs)

    @staticmethod
    def datetime_to_str(value=None):
        if value is None:
            return None
        # noinspection PyUnresolvedReferences
        return value.strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def datetime_from_str(value=None):
        if value is None:
            return None
        # noinspection PyTypeChecker
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")

    def to_str(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_str(cls, text):
        data = json.loads(text)
        return cls.from_dict(data)

    def __le__(self, other):
        assert isinstance(other, PointInfo)
        self_last = self.last
        other_last = other.last
        if self_last is None:
            return True
        elif other_last is None:
            return False
        return self_last <= other_last

    def __lt__(self, other):
        assert isinstance(other, PointInfo)
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
        assert isinstance(other, PointInfo)
        self_last = self.last
        other_last = other.last
        if self_last is None:
            return other_last is None
        elif other_last is None:
            return True
        return self_last >= other_last

    def __gt__(self, other):
        assert isinstance(other, PointInfo)
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
        assert isinstance(other, PointInfo)
        return self.last == other.last

    def __ne__(self, other):
        assert isinstance(other, PointInfo)
        return self.last != other.last


class Point(ParameterizedObject):
    parameters = ParameterizedObject.parameters + [
        Parameter(
            "check_out_of_date_backup",
            "frequency",
            converter=get_is_time_elapsed,
            help_str="frequency of backup operations. Can be an integer (number of seconds),\n"
            '"monthly:d" (at least the d-th day of each month, d = 0..28),\n'
            '"weekly:d" (the d-th day of each week, d = 0..6),\n'
            '"weekly" or "daily" (once a week or once a day),\n'
            '"daily:h" (the h-th hour of each day, h = 0..23)',
        )
    ]

    def __init__(self, name, check_out_of_date_backup=None, **kwargs):
        super(Point, self).__init__(name, **kwargs)
        self.check_out_of_date_backup = check_out_of_date_backup or get_is_time_elapsed(
            None
        )
        self.filters = []
        # list of `polyarchiv.filters.FileFilter`
        self.hooks = []
        # list of `polyarchiv.hooks.Hook`

    def add_filter(self, filter_):
        from polyarchiv.filters import FileFilter

        assert isinstance(filter_, FileFilter)
        self.filters.append(filter_)

    def add_hook(self, hook):
        from polyarchiv.hooks import Hook

        assert isinstance(hook, Hook)
        self.hooks.append(hook)
        if hook.keep_output and not self.output_temp_fd:
            self.output_temp_fd = tempfile.TemporaryFile()

    @property
    def stderr(self):
        if self.verbosity >= 3 and not self.output_temp_fd:
            return None
        elif self.output_temp_fd:
            return self.output_temp_fd
        self.output_temp_fd = open(os.devnull, "wb")
        return self.output_temp_fd

    @property
    def stdout(self):
        if self.verbosity >= 3 and not self.output_temp_fd:
            return None
        elif self.output_temp_fd:
            return self.output_temp_fd
        self.output_temp_fd = open(os.devnull, "wb")
        return self.output_temp_fd
