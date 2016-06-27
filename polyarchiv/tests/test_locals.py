# coding=utf-8
from __future__ import unicode_literals
from polyarchiv.locals import FileRepository, LocalRepository
from polyarchiv.sources import RSync
from polyarchiv.tests.test_base import FileTestCase


class TestLocalRepository(FileTestCase):

    def test_local_repository(self):
        local_repository = self.get_local_repository()
        assert isinstance(local_repository, LocalRepository)
        source = RSync('rsync', local_repository, self.original_dir_path, destination_path='rsync')
        local_repository.add_source(source)

    def get_local_repository(self):
        raise NotImplementedError


class TestFileLocalRepository(TestLocalRepository):

    def get_local_repository(self):
        return FileRepository('test_repo', local_path=self.local_repository_path, command_display=True,
                              command_keep_output=True)
