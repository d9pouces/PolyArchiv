# coding=utf-8
from __future__ import unicode_literals

from polyarchiv.points import ParameterizedObject


class Hook(ParameterizedObject):
    def __init__(self, name, **kwargs):
        super(Hook, self).__init__(name, **kwargs)
