# coding=utf-8
from __future__ import unicode_literals

import filecmp
import os
import shutil
import tempfile
from unittest import TestCase

from polyarchiv.backends import get_backend
from polyarchiv.remotes import CommonRemoteRepository


class TestBackend(TestCase):
    complete_dir_url = None
    partial_dir_url = None
    complete_file_url = None
    partial_file_url = None

    def setUp(self):
        self.original_dir_path = tempfile.mkdtemp()
        self.private_path = tempfile.mkdtemp()
        self.copy_dir_path = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile() as fd:
            self.copy_file_pth = fd.name
        self.repository = CommonRemoteRepository('remote', command_display=True)
        os.makedirs(os.path.join(self.original_dir_path, 'folder'))
        shutil.copy2(__file__, os.path.join(self.original_dir_path, 'test.py'))
        shutil.copy2(__file__, os.path.join(self.original_dir_path, 'folder', 'sub_test.py'))

    def assertEmpty(self, x):
        self.assertEqual(0, len(x))

    def assertEqualPaths(self, x, y):
        dircmp = filecmp.dircmp(x, y)
        self.assertEmpty(dircmp.left_only)
        self.assertEmpty(dircmp.right_only)
        self.assertEmpty(dircmp.diff_files)

    def test_sync_file(self):
        if self.complete_file_url is None:
            return
        backend = get_backend(self.repository, self.complete_file_url)
        backend.sync_file_from_local(__file__)
        backend.sync_file_to_local(self.copy_file_pth)
        with open(__file__, 'rb') as fd:
            orig = fd.read()
        with open(self.copy_file_pth, 'rb') as fd:
            copy = fd.read()
        self.assertEqual(orig, copy)

    def test_sync_dir(self):
        if self.complete_dir_url is None:
            return
        pass

    def tearDown(self):
        for x in (self.original_dir_path, self.private_path, self.copy_dir_path):
            if os.path.isdir(x):
                shutil.rmtree(x)


class TestFileBackend(TestBackend):
    complete_file_url = 'file:///home/vagrant/backends/files/test.py'
