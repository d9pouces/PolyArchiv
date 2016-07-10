# coding=utf-8
from __future__ import unicode_literals
import re
import os

from polyarchiv.runner import Runner
from polysphinx.nodes import EnginesHelpNode
# noinspection PyPackageRequirements
from docutils.parsers.rst.directives import unchanged_required
# noinspection PyPackageRequirements
from sphinx.util.compat import Directive

__author__ = 'Matthieu Gallet'


def regexp_check(argument):
    try:
        return re.compile(argument)
    except:
        raise ValueError


def extension_check(argument):
    if not re.match('\.[a-z0-9A-Z]+', argument):
        raise ValueError
    return argument


class EngineDirective(Directive):
    """
    Directive to insert arbitrary dot markup.
    """
    has_content = True
    required_arguments = 1
    final_argument_whitespace = False
    option_spec = {'class': unchanged_required,
                   'empty': unchanged_required,
                   'glob': unchanged_required,
                   'desc_ext': extension_check,
                   'regexp': regexp_check}

    def run(self):
        engines_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'engines.ini')
        available_local_engines, available_source_engines, available_remote_engines, available_filter_engines = \
            Runner.find_available_engines(engines_file)
        values = {'locals': available_local_engines, 'remotes': available_remote_engines,
                  'sources': available_source_engines, 'filters': available_filter_engines}
        engines = values[self.arguments[0]]

        node = EnginesHelpNode()
        node['engines'] = engines
        node['options'] = self.options
        return [node]
