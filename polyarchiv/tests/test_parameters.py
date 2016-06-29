# coding=utf-8
from __future__ import unicode_literals, print_function

import os
from unittest import TestCase

from polyarchiv.conf import Parameter
from polyarchiv.repository import ParameterizedObject
from polyarchiv.runner import Runner


class TestEngineParameters(TestCase):
    def test_engine_parameters(self):
        engines_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    'engines.ini')
        all_engines = Runner.find_available_engines(engines_file)
        for engine_dict in all_engines:
            for name, engine_cls in engine_dict.items():
                assert issubclass(engine_cls, ParameterizedObject)
                for param in engine_cls.parameters:
                    assert isinstance(param, Parameter)
