# coding=utf-8
from __future__ import unicode_literals

import codecs
import filecmp
import os
import shutil
import tempfile
from unittest import TestCase

from polyarchiv.filters import SymmetricCrypt
os.environ['PATH'] = '%s:/usr/local/bin' % os.environ['PATH']


class BaseTestFilter(TestCase):
    cls = None
    allow_in_place = True

    def setUp(self):
        self.source_path = tempfile.mkdtemp()
        self.private_path = tempfile.mkdtemp()
        self.destination_path = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.source_path, 'folder'))
        shutil.copy2(__file__, os.path.join(self.source_path, 'test.py'))
        shutil.copy2(__file__, os.path.join(self.source_path, 'folder', 'sub_test.py'))

    def assertEmpty(self, x):
        self.assertEqual(0, len(x))

    def assertEqualPaths(self, x, y):
        dircmp = filecmp.dircmp(x, y)
        print(x, y)
        print(dircmp.left_only, dircmp.right_only, dircmp.diff_files)
        self.assertEmpty(dircmp.left_only)
        self.assertEmpty(dircmp.right_only)
        self.assertEmpty(dircmp.diff_files)

    def test_filter(self):
        if self.cls is None:
            return
        filter_ = self.cls('filter', command_display=True)
        filter_.backup(self.source_path, self.private_path, allow_in_place=self.allow_in_place)
        filter_.restore(self.destination_path, self.private_path, allow_in_place=self.allow_in_place)
        self.assertEqualPaths(self.source_path, self.destination_path)

    def tearDown(self):
        for x in (self.source_path, self.private_path, self.destination_path):
            if os.path.isdir(x):
                shutil.rmtree(x)


class TestSymmetricCryptInPlace(BaseTestFilter):
    cls = SymmetricCrypt
    allow_in_place = True
