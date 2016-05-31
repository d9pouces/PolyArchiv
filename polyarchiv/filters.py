# coding=utf-8
from __future__ import unicode_literals

import codecs
import hashlib
import os
import shutil

import subprocess

from polyarchiv.conf import Parameter, check_executable, CheckOption
from polyarchiv.repository import ParameterizedObject
from polyarchiv.utils import copytree


class FileFilter(ParameterizedObject):
    work_in_place = True

    def backup(self, previous_path, private_path, allow_in_place=True):
        next_path = self.next_path(previous_path, private_path, allow_in_place)
        if self.work_in_place and not allow_in_place and \
                self.can_execute_command(['cp', '-pPR', previous_path, next_path]):
            copytree(previous_path, next_path)
        self.do_backup(previous_path, next_path, private_path, allow_in_place)
        return next_path

    def next_path(self, previous_path, private_path, allow_in_place=True):
        if not (self.work_in_place and allow_in_place):
            return private_path
        return previous_path

    def do_backup(self, previous_path, next_path, private_path, allow_in_place=True):
        raise NotImplementedError


class SymmetricCrypt(FileFilter):
    parameters = FileFilter.parameters + [
        Parameter('gpg_executable', converter=check_executable, help_str='path of the gpg executable (default: "gpg")'),
        Parameter('password', help_str='password to encrypt data'),
    ]
    work_in_place = False

    def __init__(self, name, password='password', gpg_executable='gpg', **kwargs):
        super(SymmetricCrypt, self).__init__(name, **kwargs)
        self.password = password
        self.gpg_executable = gpg_executable

    def do_backup(self, previous_path, next_path, private_path, allow_in_place=True):
        symlinks = True
        if self.can_execute_command(['rm', '-rf', next_path]):
            shutil.rmtree(next_path)
        if self.can_execute_command(['mkdir', '-p', next_path]):
            os.makedirs(next_path)
        for root, dirnames, filenames in os.walk(previous_path):
            for src_dirname in dirnames:
                src_path = os.path.join(root, src_dirname)
                dst_path = os.path.join(next_path, os.path.relpath(src_path, previous_path))
                if self.can_execute_command(['mkdir', '-p', dst_path]):
                    os.makedirs(dst_path)
                    shutil.copystat(src_path, dst_path)
            for src_filename in filenames:
                src_path = os.path.join(root, src_filename)
                dst_path = os.path.join(next_path, os.path.relpath(src_path, previous_path))
                if symlinks and os.path.islink(src_path):
                    linkto = os.readlink(src_path)
                    if self.can_execute_command(['ln', '-s', linkto, dst_path]):
                        os.symlink(linkto, dst_path)
                else:
                    cmd = ['gpg', '--passphrase', self.password, '-o', dst_path, '-c', src_path]
                    if self.can_execute_command(cmd):
                        subprocess.check_call(cmd)
                        shutil.copystat(src_path, dst_path)


class Hashsum(FileFilter):
    parameters = FileFilter.parameters + [
        Parameter('method', converter=CheckOption(['sha1', 'md5', 'sha256']), help_str='method: sha1, md5 or sha256'),
        Parameter('filename', help_str='index file (default to \'hashes.txt\')'),
    ]
    work_in_place = True

    def __init__(self, name, method='sha1', filename='hashes.txt', **kwargs):
        super(Hashsum, self).__init__(name, **kwargs)
        self.method = method
        self.filename = filename

    def do_backup(self, previous_path, next_path, private_path, allow_in_place=True):
        cmd = {'sha1': 'shasum -a 1 -b', 'md5': 'md5sum -b', 'sha256': 'shasum -a 256 -b'}[self.method]
        index_path = os.path.abspath(os.path.join(next_path, self.filename))
        fd = codecs.open(os.devnull, 'w', encoding='utf-8')
        if self.can_execute_command(['rm', index_path]):
            fd = codecs.open(index_path, 'w', encoding='utf-8')
        for root, dirnames, filenames in os.walk(next_path):
            for filename in filenames:
                src_path = os.path.abspath(os.path.join(root, filename))
                if src_path == index_path:
                    continue
                hash_obj = getattr(hashlib, self.method)()
                with open(src_path, 'rb') as src_fd:
                    for data in iter(lambda: src_fd.read(16384), b''):
                        hash_obj.update(data)
                if self.can_execute_command('%s %s >> %s' % (cmd, src_path, index_path)):
                    fd.write("%s *%s\n" % (hash_obj.hexdigest(), os.path.relpath(src_path, next_path)))
        fd.close()
