# -*- coding=utf-8 -*-
"""load a complete configuration (based on .ini files) and perform backup/restore operations
"""
from __future__ import unicode_literals

import datetime
import errno
import fnmatch
import glob
import logging
import os
import pwd
import shlex
import socket

from polyarchiv.filters import FileFilter
from polyarchiv.sources import Source

try:
    from pkg_resources import iter_entry_points
except ImportError:
    iter_entry_points = None

from polyarchiv.conf import Parameter
from polyarchiv.locals import LocalRepository
from polyarchiv.remotes import RemoteRepository
from polyarchiv.repository import ParameterizedObject, RepositoryInfo
from polyarchiv.termcolor import cprint, RED, GREEN, YELLOW
from polyarchiv.utils import import_string, text_type

try:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from configparser import RawConfigParser, Error as ConfigError
except ImportError:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from ConfigParser import RawConfigParser, Error as ConfigError

__author__ = 'Matthieu Gallet'
logger = logging.getLogger('polyarchiv.runner')


class Runner(ParameterizedObject):
    """Run backup and restore operations for all specified configurations
    """
    repository_section = 'repository'
    variables_section = 'variables'
    engine_option = 'engine'
    source_section = 'source '
    filter_section = 'filter '
    local_variables_section = 'variables '

    def __init__(self, config_directories, engines_file=None, **kwargs):
        super(Runner, self).__init__('runner', **kwargs)
        self.config_directories = config_directories
        self.available_local_engines, self.available_source_engines, self.available_remote_engines, \
            self.available_filter_engines = self.find_available_engines(engines_file)
        self.local_repositories = {}
        self.remote_repositories = {}
        self.local_config_files = []
        self.remote_config_files = []

    @staticmethod
    def find_available_engines(engines_file=None):
        available_local_engines = {}
        available_remote_engines = {}
        available_source_engines = {}
        available_filter_engines = {}
        if iter_entry_points:
            def import_points(name):
                result = {}
                for x in iter_entry_points(name):
                    # noinspection PyBroadException
                    try:
                        result[x.name.lower()] = x.load()
                    except:
                        pass
                return result

            available_local_engines.update(import_points('polyarchiv.locals'))
            available_remote_engines.update(import_points('polyarchiv.remotes'))
            available_source_engines.update(import_points('polyarchiv.sources'))
            available_filter_engines.update(import_points('polyarchiv.filters'))
        if engines_file is not None:
            parser = RawConfigParser()
            parser.read([engines_file])

            def import_items(name):
                return {key.lower(): import_string(value) for key, value in parser.items(name)} \
                    if parser.has_section(name) else {}

            available_source_engines.update(import_items('sources'))
            available_remote_engines.update(import_items('remotes'))
            available_local_engines.update(import_items('locals'))
            available_filter_engines.update(import_items('filters'))
        return available_local_engines, available_source_engines, available_remote_engines, available_filter_engines

    def load(self, show_errors=True):
        result = True
        try:
            self._find_local_repositories()
            self._find_remote_repositories()
        except ValueError as e:
            result = False
            if show_errors:
                cprint(text_type(e), RED)
        except ImportError as e:
            result = False
            if show_errors:
                cprint(text_type(e), RED)
        return result

    def _get_args_from_parser(self, config_file, parser, section, engine_cls):
        assert isinstance(parser, RawConfigParser)
        assert issubclass(engine_cls, ParameterizedObject)
        result = {'command_display': self.command_display, 'command_confirm': self.command_confirm,
                  'command_execute': self.command_execute, 'command_keep_output': self.command_keep_output}
        missing_parameters = []
        for parameter in engine_cls.parameters:
            assert isinstance(parameter, Parameter)
            option = parameter.option_name
            if not parser.has_option(section, option):
                if parameter.required:
                    missing_parameters.append(parameter.option_name)
                continue
            value = parser.get(section, option)
            try:
                result[parameter.arg_name] = parameter.converter(value)
            except ValueError as e:
                cprint('In file \'%s\', section \'%s\', option \'%s\':' % (config_file, section, option), RED)
                raise e
        if missing_parameters:
            text = 'In file \'%s\', section \'%s\', missing options \'%s\'' % (
                config_file, section, ', '.join(missing_parameters))
            raise ValueError(text)
        return result

    def _load_engine(self, config_file, parser, section, args, available_engines, expected_cls):
        if not parser.has_option(section, self.engine_option):
            msg = 'In file \'%s\', please specify the \'%s\' option in the \'%s\' section' % \
                  (config_file, self.engine_option, section)
            raise ValueError(msg)
        engine = parser.get(section, self.engine_option)
        engine_alias = engine.lower()
        if engine_alias in available_engines:
            engine_cls = available_engines[engine_alias]
        else:
            try:
                engine_cls = import_string(engine)
            except ImportError:
                cprint('List of built-in engines: %s ' % ', '.join(available_engines), GREEN)
                raise ImportError('In file \'%s\', section \'%s\': invalid engine \'%s\'' %
                                  (config_file, section, engine))
        parameters = self._get_args_from_parser(config_file, parser, section, engine_cls)
        if not issubclass(engine_cls, expected_cls):
            raise ValueError('In file \'%s\', section \'%s\': engine \'%s\' is not a subclass of \'%s\'' %
                             (config_file, section, engine, expected_cls.__name__))
        source = engine_cls(*args, **parameters)
        return source

    def _iter_config_parsers(self, pattern):
        for path in self.config_directories:
            count = 0
            for config_file in glob.glob(os.path.join(path, pattern)):
                count += 1
                parser = RawConfigParser()
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
                except ConfigError:
                    raise ValueError('File \'%s\' is not a valid \'.ini\' file' % config_file)
                logger.info('File %s added to the configuration' % config_file)
                yield config_file, parser
            if count == 0:
                logger.info('No %s file found in %s' % (pattern, path))

    @staticmethod
    def _decompose_section_name(config_file, section_name, prefix):
        if not section_name.startswith(prefix):
            return None
        values = shlex.split(section_name[len(prefix):])
        if len(values) != 1:
            raise ValueError('Ambiguous section name in file %s: \'%s\'' % (config_file, section_name))
        return values[0]

    def _find_local_repositories(self):
        now = datetime.datetime.now()
        common_values = {x: now.strftime('%' + x) for x in 'aAwdbBmyYHIpMSfzZjUWcxX'}
        # ^ all available values for datetime
        # noinspection PyBroadException
        try:
            fqdn = socket.gethostname()
        except Exception:
            fqdn = 'localhost'
        common_values.update({'fqdn': fqdn, 'hostname': fqdn.partition('.')[0]})

        for config_file, parser in self._iter_config_parsers('*.local'):
            # noinspection PyTypeChecker
            local_name = os.path.basename(config_file).rpartition('.')[0]
            local = self._load_engine(config_file, parser, self.repository_section, [local_name],
                                      self.available_local_engines, LocalRepository)
            assert isinstance(local, LocalRepository)
            # noinspection PyTypeChecker
            local.variables = {'name': local_name}
            local.variables.update(common_values)
            # load variables applying to the whole local repository
            if parser.has_section(self.variables_section):
                local.variables.update({opt: parser.get(self.variables_section, opt)
                                        for opt in parser.options(self.variables_section)})
            for section in parser.sections():
                if section == self.repository_section or section == self.variables_section:
                    continue
                used = False
                source_name = self._decompose_section_name(config_file, section, self.source_section)
                if source_name:  # section looks like [source "Database"]
                    source = self._load_engine(config_file, parser, section, [source_name, local],
                                               self.available_source_engines, Source)
                    local.add_source(source)
                    used = True
                filter_name = self._decompose_section_name(config_file, section, self.filter_section)
                if filter_name:  # section looks like [filter "sha1"]
                    filter_ = self._load_engine(config_file, parser, section, [filter_name],
                                                self.available_filter_engines, FileFilter)
                    local.add_filter(filter_)
                    used = True
                if not used:
                    cprint('Unknown section \'%s\' in file \'%s\'' % (section, config_file), YELLOW)
            self.local_config_files.append(config_file)
            self.local_repositories[local_name] = local

    def _find_remote_repositories(self):
        for config_file, parser in self._iter_config_parsers('*.remote'):
            # noinspection PyTypeChecker
            remote_name = os.path.basename(config_file).rpartition('.')[0]
            remote = self._load_engine(config_file, parser, self.repository_section, [remote_name],
                                       self.available_remote_engines, RemoteRepository)
            assert isinstance(remote, RemoteRepository)
            # load variables applying to the whole remote repository
            if parser.has_section(self.variables_section):
                remote.variables.update({opt: parser.get(self.variables_section, opt)
                                         for opt in parser.options(self.variables_section)})

            for section in parser.sections():
                filter_name = self._decompose_section_name(config_file, section, self.filter_section)
                if filter_name:  # section looks like [filter "sha1"]
                    filter_ = self._load_engine(config_file, parser, section, [filter_name],
                                                self.available_filter_engines, FileFilter)
                    remote.add_filter(filter_)
                local_name = self._decompose_section_name(config_file, section, self.local_variables_section)
                if local_name:  # section looks like [variables "local repository"]
                    remote.local_variables[local_name] = {opt: parser.get(section, opt)
                                                          for opt in parser.options(section)}
            self.remote_config_files.append(config_file)
            self.remote_repositories[remote_name] = remote

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

        :param no_remote: do not use remote repositories
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
