# coding=utf-8
from __future__ import unicode_literals

import os
import shutil
import tempfile

from polyarchiv.locals import FileRepository, LocalRepository
from polyarchiv.remotes import Synchronize, RemoteRepository
from polyarchiv.sources import RSync
from polyarchiv.tests.test_base import FileTestCase


class RemoteTestCase(FileTestCase):
    def setUp(self):
        super(RemoteTestCase, self).setUp()
        self.remote_storage_dir = tempfile.mkdtemp()
        self.metadata_storage_dir = tempfile.mkdtemp()
        self.temp_data.append(self.remote_storage_dir)
        self.temp_data.append(self.metadata_storage_dir)

    def test_remote_repository(self):
        # 1) backup
        local_repository = self.get_local_repository()
        remote_repository = self.get_remote_repository()
        if remote_repository is None:
            return
        local_repository.backup()
        assert isinstance(remote_repository, RemoteRepository)
        remote_repository.backup(local_repository, force=True)
        # 2) local remove and restore
        shutil.rmtree(self.copy_dir_path)
        os.rename(self.original_dir_path, self.copy_dir_path)
        local_repository.restore()
        self.assertEqualPaths(self.copy_dir_path, self.original_dir_path)
        # 3) remote remove and restore
        shutil.rmtree(self.original_dir_path)
        shutil.rmtree(self.local_repository_path)
        remote_repository.restore(local_repository)
        local_repository.restore()
        self.assertEqualPaths(self.copy_dir_path, self.original_dir_path)

    def get_local_repository(self):
        local_repository = FileRepository('test_repo', local_path=self.local_repository_path, command_display=True,
                                          command_keep_output=True)
        local_repository.variables.update(RemoteRepository.constant_format_values)
        source = RSync('rsync', local_repository, self.original_dir_path, destination_path='rsync')
        local_repository.add_source(source)
        return local_repository

    def get_remote_repository(self):
        return None


class SynchronizeRemoteTestCase(RemoteTestCase):
    def get_remote_repository(self):
        return Synchronize('remote', remote_url='file://%s' % self.remote_storage_dir,
                           metadata_url='file://%s/metadata.json' % self.metadata_storage_dir,
                           command_display=True, command_keep_output=False)
