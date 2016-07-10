# coding=utf-8
"""Generate the documentation for all PolyArchiv engines"""

from polysphinx.nodes import EnginesHelpNode
from polysphinx.directives import EngineDirective
from polysphinx.visitors import visit_folder_node, depart_folder_node


def setup(app):
    app.add_node(EnginesHelpNode, html=(visit_folder_node, depart_folder_node))
    app.add_directive('polyengines', EngineDirective)
