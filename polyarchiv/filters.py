# coding=utf-8
from polyarchiv.repository import ParameterizedObject


class FileFilter(ParameterizedObject):

    def __init__(self, name, **kwargs):
        super(FileFilter, self).__init__(name, **kwargs)

    def export_path(self):
        pass
