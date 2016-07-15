# coding=utf-8
from __future__ import unicode_literals

from polyarchiv._vendor.requests.packages.urllib3.packages.ordered_dict import OrderedDict
from polyarchiv.conf import Parameter

__author__ = 'Matthieu Gallet'


def render_engines_html(self, node, engines, options):
    verbose = True
    cls = ''
    if options.get('class'):
        cls = ' class="%s"' % options['class']

    content = "<dl %s>" % cls
    names = [x for x in sorted(engines.keys())]
    footnotes_indices = OrderedDict()

    def note_index(x):
        if x in footnotes_indices:
            return footnotes_indices[x]
        footnotes_indices[x] = len(footnotes_indices) + 1
        return footnotes_indices[x]

    def format_help(name_, text):
        if '[*]' in text:
            index_ = note_index('*')
            text = text.replace('[*]', '<a href="#note-%s" title="this parameter can use variables"><sup>%s</sup></a>'
                                % (index_, index_))
        if '[**]' in text:
            index_ = note_index('**')
            text = text.replace('[**]', '<a href="#note-%s" title="this parameter can use time/host-independent '
                                        'variables"><sup>%s</sup></a>' % (index_, index_))
        if name_.startswith('metadata_'):
            index_ = note_index('****')
            text += '<a href="#note-%s" title="please check the documentation about metadata"><sup>%s</sup></a>' \
                    % (index_, index_)
        if name_.endswith('_url'):
            index_ = note_index('***')
            text += '<a href="#note-%s" title="please check the documentation about URLs"><sup>%s</sup></a>' \
                    % (index_, index_)
        return text

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
                    help_str = format_help(parameter.option_name, parameter.help_str)
                    content += '<li><b %s>%s</b>: %s</li>' % (style, parameter.option_name, help_str)
                else:
                    content += '<li><b %s>%s</b></li>' % (style, parameter.option_name)
            content += '</ul></p>'

        content += '</dd>'
    content += "</dl>"
    if footnotes_indices:
        content += '<ol>'
        for footnote, index in footnotes_indices.items():
            if footnote == '*':
                content += '<li id="note-%s">this parameter can use variables</li>' % index
            elif footnote == '**':
                content += '<li id="note-%s">this parameter can use time/host-independent variables</li>' % index
            elif footnote == '***':
                content += '<li id="note-%s">please only use file/http/https/ssh URLs. If a username and a password ' \
                           'are required, their must be provided in the URL.</li>' % index
            elif footnote == '****':
                content += '<li id="note-%s">Metadata should be used if some parameters use time- or host-dependent' \
                           ' variables. This is required for restore operation.</li>' % index
        content += '</ol>'
    self.body.append(content)


def visit_folder_node(self, node):
    render_engines_html(self, node, node['engines'], node['options'])


def depart_folder_node(self, node):
    return
