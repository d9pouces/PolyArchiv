# coding=utf-8
from __future__ import unicode_literals

import filecmp
import os
import shutil
import tempfile
from unittest import TestCase


class FileTestCase(TestCase):
    dirpath = os.path.join(os.path.dirname(__file__), 'tests')

    def setUp(self):
        self.original_dir_path = tempfile.mkdtemp(prefix='original-dir')
        self.copy_dir_path = tempfile.mkdtemp(prefix='copy-dir')
        self.empty_dir_path = tempfile.mkdtemp(prefix='empty-dir')
        self.local_repository_path = tempfile.mkdtemp(prefix='local-repository')
        with tempfile.NamedTemporaryFile() as fd:
            self.copy_file_pth = fd.name
        with tempfile.NamedTemporaryFile() as fd:
            self.original_file_pth = fd.name

        os.makedirs(os.path.join(self.original_dir_path, 'folder'))
        shutil.copy2(__file__, os.path.join(self.original_dir_path, 'test.py'))
        shutil.copy2(__file__, os.path.join(self.original_dir_path, 'folder', 'sub_test.py'))
        shutil.copy2(__file__, self.original_file_pth)
        self.temp_data = [self.original_dir_path, self.copy_dir_path, self.local_repository_path,
                          self.original_file_pth, self.copy_file_pth, self.empty_dir_path, ]

    def assertEmpty(self, x):
        self.assertEqual(0, len(x))

    def assertEqualPaths(self, x, y):
        dircmp = filecmp.dircmp(x, y)
        self.assertEmpty(dircmp.left_only)
        self.assertEmpty(dircmp.right_only)
        self.assertEmpty(dircmp.diff_files)
    #
    # def tearDown(self):
    #     for path in self.temp_data:
    #         if os.path.isdir(path):
    #             shutil.rmtree(path)
    #         elif os.path.exists(path):
    #             os.remove(path)
