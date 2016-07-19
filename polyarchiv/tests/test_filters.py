# coding=utf-8
from __future__ import unicode_literals

import os
import shutil

from polyarchiv.filters import SymmetricCrypt, Hashsum
from polyarchiv.tests.test_base import FileTestCase

os.environ['PATH'] = '%s:/usr/local/bin' % os.environ['PATH']


class BaseTestFilter(FileTestCase):
    cls = None
    allow_in_place = True

    def test_filter(self):
        if self.cls is None:
            return
        filter_ = self.cls('filter', command_display=True, command_keep_output=False)
        filter_.backup(self.original_dir_path, self.collect_point_path, allow_in_place=self.allow_in_place)
        if filter_.work_in_place and self.allow_in_place:
            shutil.rmtree(self.copy_dir_path)
            shutil.copytree(self.original_dir_path, self.copy_dir_path)
            self.assertEqualPaths(self.original_dir_path, self.copy_dir_path)
        filter_.restore(self.copy_dir_path, self.collect_point_path, allow_in_place=self.allow_in_place)
        if not filter_.work_in_place or self.allow_in_place:
            self.assertEqualPaths(self.original_dir_path, self.copy_dir_path)


class TestSymmetricCryptInPlace(BaseTestFilter):
    cls = SymmetricCrypt
    allow_in_place = True


class TestSymmetricCryptNotInPlace(BaseTestFilter):
    cls = SymmetricCrypt
    allow_in_place = False


class TestHashsumInPlace(BaseTestFilter):
    cls = Hashsum
    allow_in_place = True


class TestHashsumNotInPlace(BaseTestFilter):
    cls = Hashsum
    allow_in_place = False
