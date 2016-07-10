# coding=utf-8
"""Register all components of this extension"""

from polysphinx.nodes import EnginesHelpNode
from polysphinx.directives import EngineDirective
from polysphinx.visitors import visit_folder_node, depart_folder_node

__version__ = '1.0.2'


def setup(app):
    app.add_node(EnginesHelpNode, html=(visit_folder_node, depart_folder_node))
    app.add_directive('polyengines', EngineDirective)
