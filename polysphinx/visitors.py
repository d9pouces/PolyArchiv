# coding=utf-8
from __future__ import unicode_literals

from polyarchiv.conf import Parameter

__author__ = 'Matthieu Gallet'


def render_engines_html(self, node, engines, options):
    verbose = True
    cls = ''
    if options.get('class'):
        cls = ' class="%s"' % options['class']

    content = "<dl %s>" % cls
    for name, engine_cls in engines.items():
        content += '<dt><h3>%s</h3></dt>\n' % name
        if engine_cls.__doc__:
            content += '<dd>%s' % engine_cls.__doc__.strip()
        if verbose:
            content += '<p><b>List of available parameters:</b><ul>'
            # noinspection PyUnresolvedReferences
            for parameter in sorted(engine_cls.parameters, key=lambda x: x.option_name):
                assert isinstance(parameter, Parameter)
                if parameter.common:
                    continue
                elif parameter.help_str:
                    content += '<li><b>%s</b>: %s</li>' % (parameter.option_name, parameter.help_str)
                else:
                    content += '<li><b>%s</b></li>' % parameter.option_name
            content += '</ul></p>'

        content += '</dd>'
    content += "</dl>"

    self.body.append(content)


def visit_folder_node(self, node):
    render_engines_html(self, node, node['engines'], node['options'])


def depart_folder_node(self, node):
    return
