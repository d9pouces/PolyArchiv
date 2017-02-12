# coding=utf-8
from __future__ import unicode_literals

from polyarchiv.points import ParameterizedObject


class Hook(ParameterizedObject):
    def __init__(self, name, keep_output=False, when=None, **kwargs):
        super(Hook, self).__init__(name, **kwargs)
        self.keep_output = keep_output
        self.when = when

    def call(self, when, parameterized_object, collect_point_results, backup_point_results):
        pass
