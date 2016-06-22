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
    complete_dir_path = None
    partial_dir_path = None
    complete_file_path = None
    partial_file_path = None

    def setUp(self):
        self.original_dir_path = tempfile.mkdtemp()
        self.empty_dir_path = tempfile.mkdtemp()
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
        backend.delete_on_distant()
        with open(__file__, 'rb') as fd:
            orig = fd.read()
        with open(self.copy_file_pth, 'rb') as fd:
            copy = fd.read()
        self.assertEqual(orig, copy)
        if self.complete_file_path:
            self.assertFalse(os.path.exists(self.complete_file_path))

    def test_sync_dir(self):
        if self.complete_dir_url is None:
            return
        backend = get_backend(self.repository, self.complete_dir_url)
        backend.sync_dir_from_local(self.original_dir_path)
        backend.sync_dir_to_local(self.copy_dir_path)
        self.assertEqualPaths(self.original_dir_path, self.copy_dir_path)
        backend.delete_on_distant()
        if self.complete_dir_path:
            self.assertFalse(os.path.exists(self.complete_dir_path))

    def tearDown(self):
        for x in (self.original_dir_path, self.empty_dir_path, self.copy_dir_path):
            if os.path.isdir(x):
                shutil.rmtree(x)
        if os.path.isfile(self.copy_file_pth):
            os.remove(self.copy_file_pth)


class TestFileBackend(TestBackend):
    complete_file_url = 'file:///home/vagrant/backends/files/test.py'
    complete_file_path = '/home/vagrant/backends/files/test.py'
    complete_dir_url = 'file:///home/vagrant/backends/files'
    complete_dir_path = '/home/vagrant/backends/files/'


class TestSSHBackend(TestBackend):
    complete_file_url = 'ssh://localhost/home/vagrant/backends/ssh/test.py'
    complete_file_path = '/home/vagrant/backends/ssh/test.py'
    complete_dir_url = 'ssh://localhost/home/vagrant/backends/ssh'
    complete_dir_path = '/home/vagrant/backends/ssh/'


class TestWebdavBackend(TestBackend):
    complete_file_url = 'http://testuser:toto@localhost:9012/webdav/file/test.py'
    complete_file_path = '/var/www/remotes/webdav/file/test.py'
    complete_dir_url = 'http://testuser:toto@localhost:9012/webdav/dir/'
    complete_dir_path = '/var/www/remotes/webdav/dir'
