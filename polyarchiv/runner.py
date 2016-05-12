# -*- coding=utf-8 -*-
"""load a complete configuration (based on .ini files) and perform backup/restore operations
"""
from __future__ import unicode_literals

import errno
import fnmatch
import glob
import logging
import os
import pwd

from pkg_resources import iter_entry_points

from polyarchiv.conf import Parameter
from polyarchiv.locals import LocalRepository
from polyarchiv.remotes import RemoteRepository
from polyarchiv.repository import ParameterizedObject, RepositoryInfo
from polyarchiv.termcolor import cprint, RED, GREEN
from polyarchiv.utils import import_string, text_type

try:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from configparser import ConfigParser, Error as ConfigError
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from ConfigParser import ConfigParser, Error as ConfigError

__author__ = 'mgallet'
logger = logging.getLogger('polyarchiv.runner')


class Runner(ParameterizedObject):
    """Run backup and restore operations for all specified configurations
    """
    repository_section = 'repository'
    variables_section = 'variables'
    engine_option = 'engine'

    def __init__(self, config_directories, **kwargs):
        super(Runner, self).__init__('runner', **kwargs)
        self.config_directories = config_directories
        self.available_local_engines = {x.name.lower(): x.load() for x in iter_entry_points('polyarchiv.locals')}
        self.available_remote_engines = {x.name.lower(): x.load() for x in iter_entry_points('polyarchiv.remotes')}
        self.available_source_engines = {x.name.lower(): x.load() for x in iter_entry_points('polyarchiv.sources')}
        self.local_repositories = {}
        self.remote_repositories = {}
        self.local_config_files = []
        self.remote_config_files = []

    def load(self):
        result = True
        try:
            self._find_local_repositories()
            self._find_remote_repositories()
        except ValueError as e:
            result = False
            cprint(text_type(e), RED)
        except ImportError as e:
            result = False
            cprint(text_type(e), RED)
        return result

    def _get_args_from_parser(self, config_file, parser, section, engine_cls):
        assert isinstance(parser, ConfigParser)
        assert issubclass(engine_cls, ParameterizedObject)
        result = {'command_display': self.command_display, 'command_confirm': self.command_confirm,
                  'command_execute': self.command_execute, 'command_keep_output': self.command_keep_output, }

        for parameter in engine_cls.parameters:
            assert isinstance(parameter, Parameter)
            option = parameter.option_name
            if not parser.has_option(section, option):
                continue
            value = parser.get(section, option)
            try:
                result[parameter.arg_name] = parameter.converter(value)
            except ValueError as e:
                cprint('In file ‘%s’, section ‘%s’, option ‘%s’:' % (config_file, section, option), RED)
                raise e
        return result

    def _iter_config_parsers(self, pattern):
        for path in self.config_directories:
            count = 0
            for config_file in glob.glob(os.path.join(path, pattern)):
                count += 1
                parser = ConfigParser()
                try:
                    # noinspection PyTypeChecker
                    open(config_file, 'rb').read(1)
                    parser.read([config_file])
                except IOError as e:
                    if e.errno == errno.EACCES:
                        username = pwd.getpwuid(os.getuid())[0]
                        logger.info('%s is ignored because user %s cannot read it' % (config_file, username))
                        continue
                    raise
                except ConfigError as e:
                    raise ValueError('File ‘%s’ is not a valid ‘.ini’ file' % config_file)
                logger.info('File %s added to the configuration' % config_file)
                yield config_file, parser
            if count == 0:
                logger.info('No %s file found in %s' % (pattern, path))

    def _find_local_repositories(self):
        for config_file, parser in self._iter_config_parsers('*.local'):
            if not parser.has_option(self.repository_section, self.engine_option):
                msg = 'In file ‘%s’, please specify the ‘%s’ option in the ‘%s’ section' % \
                      (config_file, self.engine_option, self.repository_section)
                raise ValueError(msg)
            engine = parser.get(self.repository_section, self.engine_option)
            engine_alias = engine.lower()
            if engine_alias in self.available_local_engines:
                engine_cls = self.available_local_engines[engine_alias]
            else:
                try:
                    engine_cls = import_string(engine)
                except ImportError:
                    cprint('List of built-in engines: %s ' % ', '.join(self.available_local_engines), GREEN)
                    msg = 'In file ‘%s’, section ‘%s’: invalid engine ‘%s’' % (config_file, self.repository_section, engine)
                    raise ImportError(msg)
            # noinspection PyTypeChecker
            name = os.path.basename(config_file).rpartition('.')[0]
            parameters = self._get_args_from_parser(config_file, parser, self.repository_section, engine_cls)
            local = engine_cls(name, **parameters)
            assert isinstance(local, LocalRepository)

            variables_section = self.variables_section
            if parser.has_section(variables_section):
                local.variables = {opt: parser.get(variables_section, opt) for opt in parser.options(variables_section)}

            for section in parser.sections():
                if section == self.repository_section or section == variables_section:
                    continue
                if not parser.has_option(section, self.engine_option):
                    msg = 'In file ‘%s’, please specify the ‘%s’ option in the ‘%s’ source' % \
                          (config_file, self.engine_option, section)
                    raise ValueError(msg)
                engine = parser.get(section, self.engine_option)
                engine_alias = engine.lower()
                if engine_alias in self.available_source_engines:
                    engine_cls = self.available_source_engines[engine_alias]
                else:
                    try:
                        engine_cls = import_string(engine)
                    except ImportError:
                        cprint('List of built-in engines: %s ' % ', '.join(self.available_source_engines), GREEN)
                        msg = 'In file ‘%s’, section ‘%s’: invalid engine ‘%s’' % \
                              (config_file, self.repository_section, engine)
                        raise ImportError(msg)
                parameters = self._get_args_from_parser(config_file, parser, section, engine_cls)
                source = engine_cls(section, local, **parameters)
                local.add_source(source)
            self.local_config_files.append(config_file)
            self.local_repositories[name] = local

    def _find_remote_repositories(self):
        for config_file, parser in self._iter_config_parsers('*.remote'):
            if not parser.has_option(self.repository_section, self.engine_option):
                msg = 'In file ‘%s’, please specify the ‘%s’ option in the ‘%s’ section' % \
                      (config_file, self.engine_option, self.repository_section)
                raise ValueError(msg)
            engine = parser.get(self.repository_section, self.engine_option)
            if engine.lower() in self.available_remote_engines:
                engine_cls = self.available_remote_engines[engine.lower()]
            else:
                try:
                    engine_cls = import_string(engine)
                except ImportError:
                    cprint('List of built-in engines: %s ' % ', '.join(self.available_remote_engines))
                    msg = 'In file ‘%s’, section ‘%s’: invalid engine ‘%s’' % (config_file, self.repository_section, engine)
                    raise ImportError(msg)
            # noinspection PyTypeChecker
            name = os.path.basename(config_file).rpartition('.')[0]
            parameters = self._get_args_from_parser(config_file, parser, self.repository_section, engine_cls)
            remote = engine_cls(name, **parameters)
            assert isinstance(remote, RemoteRepository)
            for section in parser.sections():
                if section == self.repository_section:
                    continue
                remote.local_variables[section] = {opt: parser.get(section, opt) for opt in parser.options(section)}
            self.remote_config_files.append(config_file)
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

    def backup(self, force=False, only_locals=None, only_remotes=None):
        """Run a backup operation. return two dicts
        first result is {local_repository.name: bool}  (dict["my-local_repo"] = True if successful)
        second result is {(local_repository.name, remote_repository.name): bool}

        :param force: force backup even if not out-of-date
        :param only_locals: limit to the selected local repositories
        :type only_locals: :class:`list` of `str`
        :param only_remotes: limit to the selected remote repositories
        :type only_remotes: :class:`list` of `str`
        :return:
        """
        local_results = {}
        remote_results = {}
        for local_name, local in self.local_repositories.items():
            if only_locals and local_name not in only_locals:
                continue
            assert isinstance(local, LocalRepository)
            result = local.backup(force=force)
            if result:
                logger.info('[OK] local repository %s' % local.name)
                local_results[local.name] = True
            else:
                logger.error('[KO] local repository %s' % local.name)
                local_results[local.name] = False
                continue
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes:
                    continue
                assert isinstance(remote, RemoteRepository)
                if not self.can_associate(local, remote):
                    continue
                result = remote.backup(local, force=force)
                if result:
                    logger.info('[OK] remote repository %s on local repository %s' % (remote.name, local.name))
                    remote_results[(remote.name, local.name)] = True
                else:
                    logger.error('[KO] remote repository %s on local repository %s' % (remote.name, local.name))
                    remote_results[(remote.name, local.name)] = False
        return local_results, remote_results

    def restore(self, only_locals=None, only_remotes=None, no_remote=False):
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
            if not no_remote:
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
