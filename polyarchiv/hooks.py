# coding=utf-8
from __future__ import unicode_literals

from polyarchiv.conf import Parameter, strip_split, bool_setting
from polyarchiv.points import ParameterizedObject
from polyarchiv.utils import text_type, FileContentMonitor


class Hook(ParameterizedObject):
    parameters = ParameterizedObject.parameters + [
        Parameter('events', converter=strip_split, required=True,
                  help_str='list of events (comma-separated) that trigger this hook: "before_backup",'
                           '"backup_success", "backup_error", "after_backup".'),
    ]

    def __init__(self, name, keep_output=True, events=None, **kwargs):
        super(Hook, self).__init__(name, **kwargs)
        self.keep_output = keep_output or True
        self.hooked_events = set(events)

    def call(self, parameterized_object, when, cm, collect_point_results, backup_point_results):
        assert isinstance(parameterized_object, ParameterizedObject)
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

    def __init__(self, name, path, **kwargs):
        super(LogHook, self).__init__(name, **kwargs)
        self.path = path

    def call(self, parameterized_object, when, cm, collect_point_results, backup_point_results):
        assert isinstance(cm, FileContentMonitor)
        print(parameterized_object, when, cm, collect_point_results, backup_point_results)
        with open(self.path, 'wb') as fd:
            cm.copy_content(fd, close=False)
