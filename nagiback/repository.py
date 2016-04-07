# -*- coding: utf-8 -*-
from nagiback.conf import Parameter
from nagiback.utils import get_is_time_elapsed

__author__ = 'Matthieu Gallet'


class ParameterizedObject(object):
    parameters = []

    def __init__(self, name):
        self.name = name


class RepositoryInfo(object):
    pass


class Repository(ParameterizedObject):
    parameters = ParameterizedObject.parameters + [
        Parameter('frequency', converter=get_is_time_elapsed),
    ]

    def __init__(self, name, frequency=None, ):
        super(Repository, self).__init__(name)
        self.frequency = frequency or get_is_time_elapsed('daily')
