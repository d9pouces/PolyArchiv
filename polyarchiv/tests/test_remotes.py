# coding=utf-8
from __future__ import unicode_literals

import os
import shutil
import tempfile

import subprocess

from polyarchiv.locals import FileRepository
from polyarchiv.remotes import Synchronize, RemoteRepository, GitRepository, TarArchive, RollingTarArchive
from polyarchiv.sources import LocalFiles
from polyarchiv.tests.test_base import FileTestCase


class RemoteTestCase(FileTestCase):
    def setUp(self):
        super(RemoteTestCase, self).setUp()

    @staticmethod
    def prepare():
        original_dir_path = tempfile.mkdtemp(prefix='original-dir')
        copy_dir_path = tempfile.mkdtemp(prefix='copy-dir')
        local_repository_path = tempfile.mkdtemp(prefix='local-repository')

        os.makedirs(os.path.join(original_dir_path, 'folder'))
        shutil.copy2(__file__, os.path.join(original_dir_path, 'test.py'))
        shutil.copy2(__file__, os.path.join(original_dir_path, 'folder', 'sub_test.py'))
        return original_dir_path, copy_dir_path, local_repository_path

    def test_remote_repository(self):
        original_dir_path, copy_dir_path, local_repository_path = self.prepare()
        # 1) backup
        local_repository = self.get_local_repository(original_dir_path, local_repository_path)
        remote_repository = self.get_remote_repository()
        if remote_repository is None:
            return
        local_repository.backup()
        assert isinstance(remote_repository, RemoteRepository)
        remote_repository.backup(local_repository, force=True)
        # 2) local remove and restore
        shutil.rmtree(copy_dir_path)
        os.rename(original_dir_path, copy_dir_path)
        local_repository.restore()
        self.assertEqualPaths(copy_dir_path, original_dir_path)
        # 3) remote remove and restore
        shutil.rmtree(original_dir_path)
        shutil.rmtree(local_repository_path)
        remote_repository.restore(local_repository)
        local_repository.restore()
        self.assertEqualPaths(copy_dir_path, original_dir_path)

    @staticmethod
    def get_local_repository(original_dir_path, local_repository_path):
        local_repository = FileRepository('test_repo', local_path=local_repository_path, command_display=True,
                                          command_keep_output=True)
        local_repository.variables.update(RemoteRepository.constant_format_values)
        source = LocalFiles('rsync', local_repository, original_dir_path, destination_path='rsync')
        local_repository.add_source(source)
        return local_repository

    def get_remote_repository(self):
        return None

    @staticmethod
    def get_storage_dirs():
        remote_storage_dir = tempfile.mkdtemp(prefix='remote-storage')
        metadata_storage_dir = tempfile.mkdtemp(prefix='remote-metadata')
        return remote_storage_dir, metadata_storage_dir


class SynchronizeRemoteTestCase(RemoteTestCase):
    def get_remote_repository(self):
        remote_storage_dir, metadata_storage_dir = self.get_storage_dirs()
        return Synchronize('remote', remote_url='file://%s' % remote_storage_dir,
                           metadata_url='file://%s/metadata.json' % metadata_storage_dir,
                           command_display=True, command_keep_output=False)


class GitRemoteTestCase(RemoteTestCase):
    def get_remote_repository(self):
        remote_storage_dir, metadata_storage_dir = self.get_storage_dirs()
        # return Synchronize('remote', remote_url='file://%s' % remote_storage_dir,
        #                    metadata_url='file://%s/metadata.json' % metadata_storage_dir,
        #                    command_display=True, command_keep_output=False)
        subprocess.check_call(['git', 'init', '--bare', '%s/project.git' % remote_storage_dir])
#         return GitRepository('remote', remote_url='file://%s/project.git' % remote_storage_dir,
#                              metadata_url='file://%s/metadata.json' % metadata_storage_dir,
#                              command_display=True, command_keep_output=False)


# class TarArchiveRemoteTestCase(RemoteTestCase):
#     def get_remote_repository(self):
#         return TarArchive('remote', 2remote_url='file://%s/archive.tar.gz' % self.remote_storage_dir,
#                           metadata_url='file://%s/metadata.json' % self.metadata_storage_dir,
#                           command_display=True, command_keep_output=False)
#
#
# class RollingTarArchiveRemoteTestCase(RemoteTestCase):
#     def get_remote_repository(self):
#         return RollingTarArchive('remote', remote_url='file://%s/archive.tar.gz' % self.remote_storage_dir,
#                                  metadata_url='file://%s/metadata.json' % self.metadata_storage_dir,
#                                  command_display=True, command_keep_output=False)
