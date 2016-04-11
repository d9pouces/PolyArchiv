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
from nagiback.repository import ParameterizedObject, RepositoryInfo
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
            count = 0
            for config_file in glob.glob(os.path.join(path, pattern)):
                count += 1
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
                logger.debug('file %s added to the configuration' % config_file)
                yield config_file, parser
            if count == 0:
                logger.debug('no %s file found in %s' % (pattern, path))

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

    def apply_commands(self, local_command=None, remote_command=None, local_remote_command=None,
                       only_locals=None, only_remotes=None):
        """ Apply the given commands to the available local and remote repositories.

        :param local_command: callable(local_repository) -> None
        :type local_command: `callable`
        :param local_remote_command: callable(local_repository, remote_repository) -> None
        :type local_remote_command: `callable`
        :param remote_command: callable(remote_repository) -> None
        :type remote_command: `callable`
        :param only_locals: list of selected local repositories (all if not specified)
        :type only_locals: :class:`list`
        :param only_remotes: list of selected remote repositories (all if not specified)
        :type only_remotes: :class:`list`
        :return:
        :rtype:
        """
        if remote_command:
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes:
                    continue
                assert isinstance(remote, RemoteRepository)
                remote_command(remote)
        for local_name, local in self.local_repositories.items():
            if only_locals and local_name not in only_locals:
                continue
            assert isinstance(local, LocalRepository)
            if local_command is not None:
                local_command(local)
            if local_remote_command is None:
                continue
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes:
                    continue
                assert isinstance(remote, RemoteRepository)
                if self.can_associate(local, remote):
                    local_remote_command(local, remote)

    def backup(self, only_locals=None, only_remotes=None):
        """Run a backup operation

        :param only_locals: limit to the selected local repositories
        :type only_locals: :class:`list` of `str`
        :param only_remotes: limit to the selected remote repositories
        :type only_remotes: :class:`list` of `str`
        :return:
        """
        local_failed = 0
        remote_failed = 0
        local_success = 0
        remote_success = 0
        for local_name, local in self.local_repositories.items():
            if only_locals and local_name not in only_locals:
                continue
            assert isinstance(local, LocalRepository)
            result = local.backup()
            if result:
                logger.info('[OK] local repository %s' % local.name)
                local_success += 1
            else:
                logger.error('[KO] local repository %s' % local.name)
                local_failed += 1
                continue
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes:
                    continue
                assert isinstance(remote, RemoteRepository)
                if not self.can_associate(local, remote):
                    continue
                continue
                result = remote.backup(local)
                if result:
                    logger.error('[OK] remote repository %s on local repository %s' % (remote.name, local.name))
                    remote_success += 1
                else:
                    logger.error('[KO] remote repository %s on local repository %s' % (remote.name, local.name))
                    remote_failed += 1
        return local_success, local_failed, remote_success, remote_failed

    def restore(self, only_locals=None, only_remotes=None):
        """Run a backup operation

        :param only_locals: limit to the selected local repositories
        :type only_locals: :class:`list` of `str`
        :param only_remotes: limit to the selected remote repositories
        :type only_remotes: :class:`list` of `str`
        :return:
        """
        for local_name, local in self.local_repositories.items():
            assert isinstance(local, LocalRepository)
            if only_locals and local_name not in only_locals:
                continue
            best_remote_date = None
            best_remote = None
            for remote_name, remote in self.remote_repositories.items():
                assert isinstance(remote, RemoteRepository)
                if only_remotes and remote_name not in only_remotes:
                    continue
                elif not self.can_associate(local, remote):
                    continue
                remote_info = remote.get_info(local)
                assert isinstance(remote_info, RepositoryInfo)
                if remote_info.last_success is None:
                    continue
                if best_remote_date is None or best_remote_date < remote_info.last_success:
                    best_remote = remote
                    best_remote_date = remote_info.last_success
            if best_remote is not None:
                best_remote.restore(local)
            local.restore()
