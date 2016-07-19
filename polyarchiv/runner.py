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
from polyarchiv.collect_points import CollectPoint
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
    collect_point_variables_section = 'variables '

    def __init__(self, config_directories, engines_file=None, **kwargs):
        super(Runner, self).__init__('runner', **kwargs)
        self.config_directories = config_directories
        self.available_collect_point_engines, self.available_source_engines, self.available_remote_engines, \
            self.available_filter_engines = self.find_available_engines(engines_file)
        self.collect_points = {}
        self.remote_repositories = {}
        self.collect_point_config_files = []
        self.remote_config_files = []

    @staticmethod
    def find_available_engines(engines_file=None):
        available_collect_point_engines = {}
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

            available_collect_point_engines.update(import_points('polyarchiv.collect_points'))
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
            available_collect_point_engines.update(import_items('collect_points'))
            available_filter_engines.update(import_items('filters'))
        return available_collect_point_engines, available_source_engines, available_remote_engines, available_filter_engines

    def load(self, show_errors=True):
        result = True
        try:
            self._find_collect_points()
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

    def _find_collect_points(self):
        now = datetime.datetime.now()
        common_values = {x: now.strftime('%' + x) for x in 'aAwdbBmyYHIpMSfzZjUWcxX'}
        # ^ all available values for datetime
        # noinspection PyBroadException
        try:
            fqdn = socket.gethostname()
        except Exception:
            fqdn = 'localhost'
        common_values.update({'fqdn': fqdn, 'hostname': fqdn.partition('.')[0]})

        for config_file, parser in self._iter_config_parsers('*.collect'):
            # noinspection PyTypeChecker
            collect_point_name = os.path.basename(config_file).rpartition('.')[0]
            collect_point = self._load_engine(config_file, parser, self.repository_section, [collect_point_name],
                                      self.available_collect_point_engines, CollectPoint)
            assert isinstance(collect_point, CollectPoint)
            # noinspection PyTypeChecker
            collect_point.variables = {'name': collect_point_name}
            collect_point.variables.update(common_values)
            # load variables applying to the whole collect point
            if parser.has_section(self.variables_section):
                collect_point.variables.update({opt: parser.get(self.variables_section, opt)
                                        for opt in parser.options(self.variables_section)})
            for section in parser.sections():
                if section == self.repository_section or section == self.variables_section:
                    continue
                used = False
                source_name = self._decompose_section_name(config_file, section, self.source_section)
                if source_name:  # section looks like [source "Database"]
                    source = self._load_engine(config_file, parser, section, [source_name, collect_point],
                                               self.available_source_engines, Source)
                    collect_point.add_source(source)
                    used = True
                filter_name = self._decompose_section_name(config_file, section, self.filter_section)
                if filter_name:  # section looks like [filter "sha1"]
                    filter_ = self._load_engine(config_file, parser, section, [filter_name],
                                                self.available_filter_engines, FileFilter)
                    collect_point.add_filter(filter_)
                    used = True
                if not used:
                    cprint('Unknown section \'%s\' in file \'%s\'' % (section, config_file), YELLOW)
            self.collect_point_config_files.append(config_file)
            self.collect_points[collect_point_name] = collect_point

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
                collect_point_name = self._decompose_section_name(config_file, section, self.collect_point_variables_section)
                if collect_point_name:  # section looks like [variables "collect point"]
                    remote.collect_point_variables[collect_point_name] = {opt: parser.get(section, opt)
                                                          for opt in parser.options(section)}
            self.remote_config_files.append(config_file)
            self.remote_repositories[remote_name] = remote

    @staticmethod
    def can_associate(collect_point, remote):
        """Return True if the remote can be associated to the collect point
        :param collect_point:
        :param remote:
        """
        assert isinstance(collect_point, CollectPoint)
        assert isinstance(remote, RemoteRepository)
        for collect_point_tag in collect_point.collect_point_tags:
            for remote_pattern in remote.excluded_collect_point_tags:
                if fnmatch.fnmatch(collect_point_tag, remote_pattern):
                    return False
        for remote_tag in remote.remote_tags:
            for collect_point_pattern in collect_point.excluded_remote_tags:
                if fnmatch.fnmatch(remote_tag, collect_point_pattern):
                    return False
        for collect_point_tag in collect_point.collect_point_tags:
            for remote_pattern in remote.included_collect_point_tags:
                if fnmatch.fnmatch(collect_point_tag, remote_pattern):
                    return True
        for remote_tag in remote.remote_tags:
            for collect_point_pattern in collect_point.included_remote_tags:
                if fnmatch.fnmatch(remote_tag, collect_point_pattern):
                    return True
        return False

    def apply_commands(self, collect_point_command=None, remote_command=None, collect_point_remote_command=None,
                       only_collect_points=None, only_remotes=None):
        """ Apply the given commands to the available collect/backup points.

        :param collect_point_command: callable(collect_point) -> None
        :type collect_point_command: `callable`
        :param collect_point_remote_command: callable(collect_point, remote_repository) -> None
        :type collect_point_remote_command: `callable`
        :param remote_command: callable(remote_repository) -> None
        :type remote_command: `callable`
        :param only_collect_points: list of selected collect points (all if not specified)
        :type only_collect_points: :class:`list`
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
        for collect_point_name, collect_point in self.collect_points.items():
            if only_collect_points and collect_point_name not in only_collect_points:
                continue
            assert isinstance(collect_point, CollectPoint)
            if collect_point_command is not None:
                collect_point_command(collect_point)
            if collect_point_remote_command is None:
                continue
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes:
                    continue
                assert isinstance(remote, RemoteRepository)
                if self.can_associate(collect_point, remote):
                    collect_point_remote_command(collect_point, remote)

    def backup(self, force=False, only_collect_points=None, only_remotes=None, skip_collect=False, skip_remote=False):
        """Run a backup operation. return two dicts
        first result is {collect_point.name: bool}  (dict["my-collect_repo"] = True if successful)
        second result is {(collect_point.name, remote_repository.name): bool}

        :param force: force backup even if not out-of-date
        :param only_collect_points: limit to the selected collect points
        :type only_collect_points: :class:`list` of `str`
        :param only_remotes: limit to the selected remote repositories
        :type only_remotes: :class:`list` of `str`
        :param skip_collect: do not execute the collect point phase
        :param skip_remote: do not execute the backup point phase
        :return:
        """
        collect_point_results = {}
        remote_results = {}
        for collect_point_name, collect_point in self.collect_points.items():
            if only_collect_points and collect_point_name not in only_collect_points:
                continue
            assert isinstance(collect_point, CollectPoint)
            if not skip_collect:
                result = collect_point.backup(force=force)
                if result:
                    logger.info('[OK] collect point %s' % collect_point.name)
                    collect_point_results[collect_point.name] = True
                else:
                    logger.error('[KO] collect point %s' % collect_point.name)
                    collect_point_results[collect_point.name] = False
                    continue
            for remote_name, remote in self.remote_repositories.items():
                if only_remotes and remote_name not in only_remotes and not skip_remote:
                    continue
                assert isinstance(remote, RemoteRepository)
                if not self.can_associate(collect_point, remote):
                    continue
                result = remote.backup(collect_point, force=force)
                if result:
                    logger.info('[OK] remote repository %s on collect point %s' % (remote.name, collect_point.name))
                    remote_results[(remote.name, collect_point.name)] = True
                else:
                    logger.error('[KO] remote repository %s on collect point %s' % (remote.name, collect_point.name))
                    remote_results[(remote.name, collect_point.name)] = False
        return collect_point_results, remote_results

    def restore(self, only_collect_points=None, only_remotes=None, no_remote=False):
        """Run a backup operation

        :param no_remote: do not use remote repositories
        :param only_collect_points: limit to the selected collect points
        :type only_collect_points: :class:`list` of `str`
        :param only_remotes: limit to the selected remote repositories
        :type only_remotes: :class:`list` of `str`
        :return:
        """
        for collect_point_name, collect_point in self.collect_points.items():
            assert isinstance(collect_point, CollectPoint)
            if only_collect_points and collect_point_name not in only_collect_points:
                continue
            best_remote_date = None
            best_remote = None
            if not no_remote:
                for remote_name, remote in self.remote_repositories.items():
                    assert isinstance(remote, RemoteRepository)
                    if only_remotes and remote_name not in only_remotes:
                        continue
                    elif not self.can_associate(collect_point, remote):
                        continue
                    remote_info = remote.get_info(collect_point)
                    assert isinstance(remote_info, RepositoryInfo)
                    if remote_info.last_success is None:
                        continue
                    if best_remote_date is None or best_remote_date < remote_info.last_success:
                        best_remote = remote
                        best_remote_date = remote_info.last_success
                if best_remote is not None:
                    best_remote.restore(collect_point)
            collect_point.restore()
