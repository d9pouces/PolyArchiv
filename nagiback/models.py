# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import fnmatch
import glob
import os
from inspect import signature, Signature

from nagiback.locals import LocalRepository
from nagiback.remotes import RemoteRepository
from nagiback.utils import import_string

try:
    from configparser import ConfigParser
except ImportError:
    # noinspection PyUnresolvedReferences
    from ConfigParser import ConfigParser

__author__ = 'mgallet'


class Configuration(object):
    global_section = 'global'

    def __init__(self, config_directories):
        self.config_directories = config_directories
        self.local_repositories = []
        self.remote_repositories = []
        self._find_local_repositories()
        self._find_remote_repositories()

    @staticmethod
    def _get_args_from_parser(parser, section, sig):
        assert isinstance(sig, Signature)
        assert isinstance(parser, ConfigParser)
        return {arg_name: parser.get(section, arg_name) for arg_name in sig.parameters}

    def _find_local_repositories(self):
        for path in self.config_directories:
            for config_file in glob.glob(os.path.join(path, '*.local')):
                parser = ConfigParser()
                parser.read([config_file])
                engine = parser.get(self.global_section, 'engine', fallback='nagiback.locals.GitRepository')
                engine_cls = import_string(engine)
                sig = signature(engine_cls)
                local = engine_cls(**self._get_args_from_parser(parser, self.global_section, sig))
                self.local_repositories.append(local)
                for section in parser.sections():
                    if section != self.global_section and parser.has_option(section, 'engine'):
                        engine_cls = import_string(parser.get(section, 'engine'))
                        sig = signature(engine_cls)
                        source = sig(local, **self._get_args_from_parser(parser, section, sig))
                        local.add_source(source)

    def _find_remote_repositories(self):
        for path in self.config_directories:
            for config_file in glob.glob(os.path.join(path, '*.remote')):
                parser = ConfigParser()
                parser.read([config_file])
                engine = parser.get(self.global_section, 'engine', fallback='nagiback.remotes.GitRepository')
                engine_cls = import_string(engine)
                sig = signature(engine_cls)
                remote = engine_cls(**self._get_args_from_parser(parser, self.global_section, sig))
                self.remote_repositories.append(remote)

    @staticmethod
    def can_associate(local, remote):
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

    def run(self):
        for local in self.local_repositories:
            assert isinstance(local, LocalRepository)
            local.run()
            for remote in self.remote_repositories:
                assert isinstance(remote, RemoteRepository)
                if self.can_associate(local, remote):
                    remote.run(local)
