# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import fnmatch
import glob
import logging
import os
import errno

from nagiback.conf import Parameter
from nagiback.locals import LocalRepository
from nagiback.remotes import RemoteRepository
from nagiback.repository import ParameterizedObject
from nagiback.utils import import_string

try:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from configparser import ConfigParser
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from ConfigParser import ConfigParser

__author__ = 'mgallet'
logger = logging.getLogger('nagiback.runner')


class Runner(object):
    """Run backup and restore operations for all specified configurations
    """
    global_section = 'global'
    engine_option = 'engine'

    def __init__(self, config_directories):
        self.config_directories = config_directories
        self.local_repositories = {}
        self.remote_repositories = {}
        self._find_local_repositories()
        self._find_remote_repositories()
        self.local_config_files = []
        self.remote_config_files = []

    @staticmethod
    def _get_args_from_parser(parser, section, engine_cls):
        assert isinstance(parser, ConfigParser)
        assert issubclass(engine_cls, ParameterizedObject)
        result = {}
        for parameter in engine_cls.parameters:
            assert isinstance(parameter, Parameter)
            if not parser.has_option(section, parameter.option_name):
                continue
            result[parameter.arg_name] = parameter.converter(parser.get(section, parameter.option_name))
        return result

    def _find_local_repositories(self):
        for path in self.config_directories:
            for config_file in glob.glob(os.path.join(path, '*.local')):
                parser = ConfigParser()
                try:
                    parser.read([config_file])
                except IOError as e:
                    if e.errno == errno.EACCES:
                        continue
                    raise
                self.local_config_files.append(config_file)
                engine = parser.get(self.global_section, self.engine_option, fallback='nagiback.locals.GitRepository')
                engine_cls = import_string(engine)
                name = os.path.basename(config_file).rpartition('.')[0]
                parameters = self._get_args_from_parser(parser, self.global_section, engine_cls)
                local = engine_cls(name, **parameters)
                self.local_repositories[name] = local
                for section in parser.sections():
                    if section == self.global_section or not parser.has_option(section, 'engine'):
                        continue
                    engine_cls = import_string(parser.get(section, self.engine_option))
                    parameters = self._get_args_from_parser(parser, section, engine_cls)
                    source = engine_cls(section, local, **parameters)
                    local.add_source(source)

    def _find_remote_repositories(self):
        for path in self.config_directories:
            for config_file in glob.glob(os.path.join(path, '*.remote')):
                parser = ConfigParser()
                try:
                    parser.read([config_file])
                except IOError as e:
                    if e.errno == errno.EACCES:
                        continue
                    raise
                self.remote_config_files.append(config_file)
                engine = parser.get(self.global_section, self.engine_option, fallback='nagiback.remotes.GitRepository')
                engine_cls = import_string(engine)
                name = os.path.basename(config_file).rpartition('.')[0]
                parameters = self._get_args_from_parser(parser, self.global_section, engine_cls)
                remote = engine_cls(name, **parameters)
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
