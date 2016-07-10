# coding=utf-8
from __future__ import unicode_literals

from polyarchiv.conf import Parameter

__author__ = 'Matthieu Gallet'


def render_engines_html(self, node, engines, options):
    verbose = True
    cls = ''
    if options.get('class'):
        cls = ' class="%s"' % options['class']
    footnotes = 0
    content = "<dl %s>" % cls
    names = [x for x in sorted(engines.keys())]
    for name in names:
        engine_cls = engines[name]
        content += '<dt><h3>engine=%s</h3></dt>\n' % name
        if engine_cls.__doc__:
            content += '<dd>%s' % engine_cls.__doc__.strip()
        if verbose:
            content += '<p><b>List of available parameters:</b><ul>'
            # noinspection PyUnresolvedReferences
            for parameter in sorted(engine_cls.parameters, key=lambda x: x.option_name):
                assert isinstance(parameter, Parameter)
                if parameter.required:
                    style = 'style="color: #C55;"'
                else:
                    style = 'style="color: #555;"'
                if parameter.common:
                    continue
                elif parameter.help_str:
                    help_str, footnote = format_help(parameter.help_str)
                    content += '<li><b %s>%s</b>: %s</li>' % (style, parameter.option_name, help_str)
                    footnotes |= footnote
                else:
                    content += '<li><b %s>%s</b></li>' % (style, parameter.option_name)
            content += '</ul></p>'

        content += '</dd>'
    content += "</dl>"
    if footnotes:
        content += '<ol>'
        if footnotes & 1:
            content += '<li id="note-1">this parameter can use variables</li>'
        if footnotes & 2:
            content += '<li id="note-2">this parameter can use time/host-independent variables</li>'
        content += '</ol>'
    self.body.append(content)


def format_help(text):
    has_footnote = 0
    if '[*]' in text:
        has_footnote = 1
        text = text.replace('[*]', '<a href="#note-1" title="this parameter can use variables"><sup>1</sup></a>')
    if '[**]' in text:
        has_footnote = 2
        text = text.replace('[**]', '<a href="#note-2" title="this parameter can use time/host-independent '
                                    'variables"><sup>2</sup></a>')
    return text, has_footnote


def visit_folder_node(self, node):
    render_engines_html(self, node, node['engines'], node['options'])


def depart_folder_node(self, node):
    return
