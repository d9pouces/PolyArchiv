# coding=utf-8
from __future__ import unicode_literals

import smtplib
from email.mime.text import MIMEText

from polyarchiv.conf import Parameter, strip_split
from polyarchiv.points import ParameterizedObject
from polyarchiv.utils import text_type, FileContentMonitor


class Hook(ParameterizedObject):
    parameters = ParameterizedObject.parameters + [
        Parameter('events', converter=strip_split, required=True,
                  help_str='list of events (comma-separated) that trigger this hook: "before_backup",'
                           '"backup_success", "backup_error", "after_backup".'),
    ]
    keep_output = True

    def __init__(self, name, runner, parameterized_object, events=None, **kwargs):
        super(Hook, self).__init__(name, **kwargs)
        assert isinstance(parameterized_object, ParameterizedObject)
        self.runner = runner
        self.parameterized_object = parameterized_object
        self.hooked_events = set(events)

    def stderr(self):
        return self.runner.stderr

    def stdout(self):
        return self.runner.stdout

    def print_message(self, *args, **kwargs):
        return self.runner.print_message(*args, **kwargs)

    @property
    def variables(self):
        return self.parameterized_object.variables

    def call(self, when, cm, collect_point_results, backup_point_results):
        assert isinstance(when, text_type)
        assert isinstance(cm, FileContentMonitor)
        assert isinstance(collect_point_results, dict)  # dict[collect_point.name] = True/False
        assert isinstance(backup_point_results, dict)  # dict[(backup_point.name, collect_point.name)] = True/False
        raise NotImplementedError


class LogHook(Hook):
    """store PolyArchiv's output to the given path. Be sure to set `keep_output` to `y`."""
    parameters = Hook.parameters + [
        Parameter('path', required=True,
                  help_str='path of the log file'),
    ]

    def __init__(self, name, runner, path=None, **kwargs):
        super(LogHook, self).__init__(name, runner, **kwargs)
        self.path = path

    def call(self, when, cm, collect_point_results, backup_point_results):
        assert isinstance(cm, FileContentMonitor)
        with open(self.path, 'wb') as fd:
            cm.copy_content(fd, close=False)


class EmailHook(Hook):
    """store PolyArchiv's output to the given path. Be sure to set `keep_output` to `y`."""
    parameters = Hook.parameters + [
        Parameter('recipient', required=True, help_str='destination (multiple value must be separated by commas)'),
        Parameter('path', required=True,
                  help_str='path of the log file'),
    ]

    def __init__(self, name, runner, path=None, **kwargs):
        super(EmailHook, self).__init__(name, runner, **kwargs)
        self.path = path

    def call(self, when, cm, collect_point_results, backup_point_results):
        assert isinstance(cm, FileContentMonitor)
        content = cm.get_text_content()
        msg = MIMEText(content)
        # me == the sender's email address
        # you == the recipient's email address
        msg['Subject'] = 'The contents of %s' % textfile
        msg['From'] = me
        msg['To'] = you

        # Send the message via our own SMTP server.
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()
