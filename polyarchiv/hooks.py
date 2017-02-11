# coding=utf-8
from __future__ import unicode_literals

from polyarchiv.points import ParameterizedObject


class Hook(ParameterizedObject):
    def __init__(self, name, keep_output=False, when=None, **kwargs):
        super(Hook, self).__init__(name, **kwargs)
        self.keep_output = keep_output
        self.when = when

    def do_backup(self, previous_path, next_path, private_path, allow_in_place=True):
        raise NotImplementedError

    def do_restore(self, previous_path, next_path, private_path, allow_in_place=True):
        raise NotImplementedError

