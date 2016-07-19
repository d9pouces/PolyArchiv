# coding=utf-8
from __future__ import unicode_literals

import os
import shutil

from polyarchiv.collect_points import FileRepository, CollectPoint, GitRepository, ArchiveRepository
from polyarchiv.remotes import RemoteRepository
from polyarchiv.sources import LocalFiles
from polyarchiv.tests.test_base import FileTestCase


class TestCollectPoint(FileTestCase):

    def test_collect_point(self):
        collect_point = self.get_collect_point()
        if collect_point is None:
            return
        assert isinstance(collect_point, CollectPoint)
        collect_point.variables.update(RemoteRepository.constant_format_values)
        source = LocalFiles('rsync', collect_point, self.original_dir_path, destination_path='rsync')
        collect_point.add_source(source)
        collect_point.backup()
        shutil.rmtree(self.copy_dir_path)
        os.rename(self.original_dir_path, self.copy_dir_path)
        collect_point.restore()
        self.assertEqualPaths(self.copy_dir_path, self.original_dir_path)

    def get_collect_point(self):
        return None


class TestFileCollectPoint(TestCollectPoint):

    def get_collect_point(self):
        return FileRepository('test_repo', local_path=self.collect_point_path, command_display=True,
                              command_keep_output=True)


class TestGitCollectPoint(TestCollectPoint):

    def get_collect_point(self):
        return GitRepository('test_repo', local_path=self.collect_point_path, command_display=True,
                             command_keep_output=True)


class TestArchiveCollectPoint(TestCollectPoint):

    def get_collect_point(self):
        return ArchiveRepository('test_repo', local_path=self.collect_point_path, command_display=True,
                                 command_keep_output=True)
