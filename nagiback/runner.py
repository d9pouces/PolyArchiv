# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import fnmatch
import glob
import os
from inspect import signature, Signature, Parameter

from nagiback.locals import LocalRepository
from nagiback.remotes import RemoteRepository
from nagiback.utils import import_string

try:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from configparser import ConfigParser
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from ConfigParser import ConfigParser

__author__ = 'mgallet'


class Runner(object):
    """Run backup and restore operations for all specified configurations
    """
    global_section = 'global'

    def __init__(self, config_directories):
        self.config_directories = config_directories
        self.local_repositories = {}
        self.remote_repositories = {}
        self._find_local_repositories()
        self._find_remote_repositories()

    @staticmethod
    def _get_args_from_parser(parser, section, sig):
        assert isinstance(sig, Signature)
        assert isinstance(parser, ConfigParser)
        values = {}
        if any(x.kind == Parameter.VAR_KEYWORD for x in sig.parameters):
            pass
        for parameter in sig.parameters:
            pass

        return {arg_name: parser.get(section, arg_name) for arg_name in sig.parameters
                if parser.has_option(section, arg_name)}

    def _find_local_repositories(self):
        for path in self.config_directories:
            for config_file in glob.glob(os.path.join(path, '*.local')):
                parser = ConfigParser()
                parser.read([config_file])
                engine = parser.get(self.global_section, 'engine', fallback='nagiback.locals.GitRepository')
                engine_cls = import_string(engine)
                sig = signature(engine_cls)
                name = os.path.basename(config_file).rpartition('.')[0]
                local = engine_cls(name, **self._get_args_from_parser(parser, self.global_section, sig))
                self.local_repositories[name] = local
                for section in parser.sections():
                    if section == self.global_section or not parser.has_option(section, 'engine'):
                        continue
                    engine_cls = import_string(parser.get(section, 'engine'))
                    sig = signature(engine_cls)
                    source = sig(section, local, **self._get_args_from_parser(parser, section, sig))
                    local.add_source(source)

    def _find_remote_repositories(self):
        for path in self.config_directories:
            for config_file in glob.glob(os.path.join(path, '*.remote')):
                parser = ConfigParser()
                parser.read([config_file])
                engine = parser.get(self.global_section, 'engine', fallback='nagiback.remotes.GitRepository')
                engine_cls = import_string(engine)
                sig = signature(engine_cls)
                name = os.path.basename(config_file).rpartition('.')[0]
                remote = engine_cls(name, **self._get_args_from_parser(parser, self.global_section, sig))
                self.remote_repositories[name] = remote

    @staticmethod
    def can_associate(local, remote):
        """Return True if the remote can be associated to the local repository"""
        assert isinstance(local, LocalRepository)
        assert isinstance(remote, RemoteRepository)
        for local_tag in local.local_tags:
            for remote_pattern in remote.excluded_local_tags:
                if fnmatch.fnmatch(local_tag, remote_pattern):
                    return False
        for remote_tag in remote.remote_tags:
            for local_pattern in local.excluded_remote_tags:
                if fnmatch.fnmatch(remote_tag, local_pattern):
                    return False
        for local_tag in local.local_tags:
            for remote_pattern in remote.included_local_tags:
                if fnmatch.fnmatch(local_tag, remote_pattern):
                    return True
        for remote_tag in remote.remote_tags:
            for local_pattern in local.included_remote_tags:
                if fnmatch.fnmatch(remote_tag, local_pattern):
                    return True
        return False

    def backup(self, only_locals=None, only_remotes=None):
        """Run a backup operation

        :param only_locals: limit to the selected local repositories
        :type only_locals: :class:`list` of `str`
        :param only_remotes: limit to the selected remote repositories
        :type only_remotes: :class:`list` of `str`
        :return:
        """
        for local_name, local in self.local_repositories.items():
            if only_locals and local_name not in only_locals:
                continue
            assert isinstance(local, LocalRepository)
            local.backup()
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes:
                    continue
                assert isinstance(remote, RemoteRepository)
                if self.can_associate(local, remote):
                    remote.backup(local)
