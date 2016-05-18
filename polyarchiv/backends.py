# coding=utf-8
"""Storage backend for two kinds of remote repositories:

    * SmartArchive
    * Synchronize

These backends are based on ssh, webdav, ftp and file

Authentication methods:

    * ssh: username:private_key or username:password
    * webdav: username:password + ca_cert
    * ftp: username:password + ca_cert
    * file: no auth

"""
from __future__ import unicode_literals
import os
import shutil

import posix

import subprocess
from xml.dom.minidom import parseString


class StorageBackend(object):
    def __init__(self, repository):
        from polyarchiv.repository import Repository
        assert isinstance(repository, Repository)
        self.repository = repository

    def can_execute_command(self, text):
        return self.repository.can_execute_command(text)

    def execute_command(self, cmd, ignore_errors=False, cwd=None, stderr=None, stdout=None, stdin=None, env=None,
                        error_str=None):
        return self.repository.execute_command(cmd, ignore_errors=ignore_errors, cwd=cwd, stderr=stderr,
                                               stdout=stdout, stdin=stdin, env=env, error_str=error_str)

    def listdir(self, path):
        raise NotImplementedError

    def stat(self, path):
        raise NotImplementedError

    def copy_to(self, src, dst):
        raise NotImplementedError

    def copy_from(self, src, dst):
        raise NotImplementedError

    def makedirs(self, path):
        raise NotImplementedError

    def remove(self, path):
        raise NotImplementedError

    def rename(self, src, dst):
        raise NotImplementedError


class FileStorageBackend(StorageBackend):
    def __init__(self, repository, root):
        super(FileStorageBackend, self).__init__(repository)
        self.root = root

    def abspath(self, path):
        return os.path.join(self.root, os.path.abspath('%s%s' % (os.path.sep, path)))

    def stat(self, path):
        abspath = self.abspath(path)
        if not os.path.exists(abspath):
            return None
        return os.stat(abspath)

    def makedirs(self, path):
        abspath = self.abspath(path)
        if not os.path.isdir(abspath) and self.can_execute_command(['mkdir', '-p', abspath]):
            os.makedirs(abspath)

    def remove(self, path):
        abspath = self.abspath(path)
        if os.path.isdir(abspath) and self.can_execute_command(['rm', '-rf', abspath]):
            shutil.rmtree(abspath)
        elif os.path.isfile(abspath) and self.can_execute_command(['rm', '-f', abspath]):
            os.remove(abspath)

    def copy_to(self, src, dst):
        self.makedirs(posix.path.dirname(dst))
        abspath = self.abspath(dst)
        if self.can_execute_command(['cp', src, abspath]):
            shutil.copy(src, abspath)

    def copy_from(self, src, dst):
        abspath = self.abspath(src)
        if self.can_execute_command(['cp', abspath, dst]):
            shutil.copy(abspath, dst)

    def listdir(self, path):
        abspath = self.abspath(path)
        values = os.listdir(abspath)
        dirnames, filenames = [], []
        for x in values:
            if os.path.isdir(os.path.join(abspath, x)):
                dirnames.append(x)
            elif os.path.isfile(os.path.join(abspath, x)):
                filenames.append(x)
        return path, dirnames, filenames

    def rename(self, src, dst):
        self.makedirs(os.path.dirname(dst))
        src = self.abspath(src)
        dst = self.abspath(dst)
        if self.can_execute_command(['mv', src, dst]):
            os.rename(src, dst)


class WebdavStorageBackend(StorageBackend):
    def __init__(self, repository, root, curl_executable='curl', username='', password=''):
        super(WebdavStorageBackend, self).__init__(repository)
        if root.endswith('/'):
            root = root[:-1]
        self.root = root
        self.curl_executable = curl_executable
        self.username = username
        self.password = password

    def abspath(self, path):
        return os.path.join(self.root, posix.path.abspath('/%s' % path))

    def curl_cmd(self, *args):
        return [self.curl_executable, '-u', '%s:%s' % (self.username, self.password)] + [x for x in args]

    def copy_from(self, src, dst):
        self.execute_command(self.curl_cmd('-o', dst, self.abspath(src)))

    def copy_to(self, src, dst):
        self.execute_command(self.curl_cmd('-T', src, self.abspath(dst)))

    def makedirs(self, path):
        self.execute_command(self.curl_cmd('-X', 'MKCOL', self.abspath(path)))

    def rename(self, src, dst):
        self.execute_command(
            self.curl_cmd('-X', 'MOVE', '--header', 'Destination: %s' % self.abspath(dst), self.abspath(src)))

    def remove(self, path):
        self.execute_command(self.curl_cmd('-X', 'DELETE', '--header', 'Depth: infinity', self.abspath(path)))

    def listdir(self, path):
        cmd = self.curl_cmd('-X', 'PROPFIND', self.abspath(path))
        p = subprocess.Popen(cmd)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise ValueError('Unable to get properties of %s' % self.abspath(path))
        content = stdout.decode('utf-8')
        xml_content = parseString(content)
        dirnames, filenames = [], []
        for response in xml_content.getElementsByTagName('D:response'):
            href = response.getElementsByTagName('D:href')[0]
            print(href.childNodes[0].data)
        return path, dirnames, filenames


class SSHStorageBackend(StorageBackend):
    pass


class FTPStorageBackend(StorageBackend):
    pass
