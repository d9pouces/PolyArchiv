# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import fnmatch
import glob
import logging
import os
import errno
import pwd

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
        self.local_config_files = []
        self.remote_config_files = []
        self._find_local_repositories()
        self._find_remote_repositories()

    @staticmethod
    def _get_args_from_parser(config_file, parser, section, engine_cls):
        assert isinstance(parser, ConfigParser)
        assert issubclass(engine_cls, ParameterizedObject)
        result = {}
        for parameter in engine_cls.parameters:
            assert isinstance(parameter, Parameter)
            option = parameter.option_name
            if not parser.has_option(section, option):
                continue
            value = parser.get(section, option)
            try:
                result[parameter.arg_name] = parameter.converter(value)
            except ValueError as e:
                logger.critical('Error in %s, section [%s], value %s: %s' % (config_file, section, option, value))
                raise e
        return result

    def _iter_config_parsers(self, pattern):
        for path in self.config_directories:
            for config_file in glob.glob(os.path.join(path, pattern)):
                parser = ConfigParser()
                try:
                    open(config_file, 'rb').read(1)
                    parser.read([config_file])
                except IOError as e:
                    if e.errno == errno.EACCES:
                        username = pwd.getpwuid(os.getuid())[0]
                        logger.debug('%s is ignored because user %s cannot read it' % (config_file, username))
                        continue
                    raise
                logger.debug('File %s added to the configuration' % config_file)
                yield config_file, parser

    def _find_local_repositories(self):
        for config_file, parser in self._iter_config_parsers('*.local'):
            self.local_config_files.append(config_file)
            engine = parser.get(self.global_section, self.engine_option)
            engine_cls = import_string(engine)
            name = os.path.basename(config_file).rpartition('.')[0]
            parameters = self._get_args_from_parser(config_file, parser, self.global_section, engine_cls)
            local = engine_cls(name, **parameters)
            self.local_repositories[name] = local
            for section in parser.sections():
                if section == self.global_section or not parser.has_option(section, 'engine'):
                    continue
                engine_cls = import_string(parser.get(section, self.engine_option))
                parameters = self._get_args_from_parser(config_file, parser, section, engine_cls)
                source = engine_cls(section, local, **parameters)
                local.add_source(source)

    def _find_remote_repositories(self):
        for config_file, parser in self._iter_config_parsers('*.remote'):
            self.remote_config_files.append(config_file)
            engine = parser.get(self.global_section, self.engine_option)
            engine_cls = import_string(engine)
            name = os.path.basename(config_file).rpartition('.')[0]
            parameters = self._get_args_from_parser(config_file, parser, self.global_section, engine_cls)
            remote = engine_cls(name, **parameters)
            self.remote_repositories[name] = remote

    @staticmethod
    def can_associate(local, remote):
        """Return True if the remote can be associated to the local repository
        :param local:
        :param remote:
        """
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

    def apply_commands(self, local_command, remote_command, only_locals=None, only_remotes=None):
        """ Apply the given commands to the available local and remote repositories.

        :param local_command: callable(local_repository) -> None
        :type local_command: `callable`
        :param remote_command: callable(local_repository, remote_repository) -> None
        :type remote_command: `callable`
        :param only_locals:
        :type only_locals:
        :param only_remotes:
        :type only_remotes:
        :return:
        :rtype:
        """
        for local_name, local in self.local_repositories.items():
            if only_locals and local_name not in only_locals:
                continue
            assert isinstance(local, LocalRepository)
            if local_command is not None:
                local_command(local)
            if remote_command is None:
                continue
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes:
                    continue
                assert isinstance(remote, RemoteRepository)
                if self.can_associate(local, remote):
                    remote_command(local, remote)

    def backup(self, only_locals=None, only_remotes=None):
        """Run a backup operation

        :param only_locals: limit to the selected local repositories
        :type only_locals: :class:`list` of `str`
        :param only_remotes: limit to the selected remote repositories
        :type only_remotes: :class:`list` of `str`
        :return:
        """
        self.apply_commands(lambda local: local.backup(), lambda local, remote: remote.backup(local),
                            only_locals=only_locals, only_remotes=only_remotes)
