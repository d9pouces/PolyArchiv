# coding=utf-8
from __future__ import unicode_literals

import os
import shutil
import tempfile

import subprocess

from polyarchiv.collect_points import FileRepository
from polyarchiv.remotes import Synchronize, RemoteRepository, GitRepository, TarArchive, RollingTarArchive
from polyarchiv.sources import LocalFiles
from polyarchiv.tests.test_base import FileTestCase


class RemoteTestCase(FileTestCase):

    def test_remote_repository(self):
        original_dir_path, copy_dir_path, collect_point_path = self.prepare()
        # 1) backup
        collect_point = self.get_collect_point(original_dir_path, collect_point_path)
        remote_repository = self.get_remote_repository()
        if remote_repository is None:
            return
        collect_point.backup()
        assert isinstance(remote_repository, RemoteRepository)
        remote_repository.backup(collect_point, force=True)
        # 2) local remove and restore
        shutil.rmtree(copy_dir_path)
        os.rename(original_dir_path, copy_dir_path)
        collect_point.restore()
        self.assertEqualPaths(copy_dir_path, original_dir_path)
        # 3) remote remove and restore
        shutil.rmtree(original_dir_path)
        shutil.rmtree(collect_point_path)
        remote_repository.restore(collect_point)
        collect_point.restore()
        self.assertEqualPaths(copy_dir_path, original_dir_path)

    @staticmethod
    def get_collect_point(original_dir_path, collect_point_path):
        collect_point = FileRepository('test_repo', local_path=collect_point_path, command_display=True,
                                          command_keep_output=True)
        collect_point.variables.update(RemoteRepository.constant_format_values)
        source = LocalFiles('rsync', collect_point, original_dir_path, destination_path='rsync')
        collect_point.add_source(source)
        return collect_point

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
        subprocess.check_call(['git', 'init', '--bare', '%s/project.git' % remote_storage_dir])
        return GitRepository('remote', remote_url='file://%s/project.git' % remote_storage_dir,
                             metadata_url='file://%s/metadata.json' % metadata_storage_dir,
                             command_display=True, command_keep_output=False)


class TarArchiveRemoteTestCase(RemoteTestCase):
    def get_remote_repository(self):
        remote_storage_dir, metadata_storage_dir = self.get_storage_dirs()
        return TarArchive('remote', remote_url='file://%s/archive.tar.gz' % remote_storage_dir,
                          metadata_url='file://%s/metadata.json' % metadata_storage_dir,
                          command_display=True, command_keep_output=False)


class RollingTarArchiveRemoteTestCase(RemoteTestCase):
    def get_remote_repository(self):
        remote_storage_dir, metadata_storage_dir = self.get_storage_dirs()
        return RollingTarArchive('remote', remote_url='file://%s/archive.tar.gz' % remote_storage_dir,
                                 metadata_url='file://%s/metadata.json' % metadata_storage_dir,
                                 command_display=True, command_keep_output=False)
