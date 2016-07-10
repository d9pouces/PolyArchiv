# -*- coding=utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
import re
import shutil
import sys

from pip._vendor.distlib.compat import raw_input

__author__ = 'Matthieu Gallet'

if sys.version_info[0] == 3:
    text_type = str
else:
    # noinspection PyUnresolvedReferences
    text_type = unicode


def get_input_text(prompt):
    encoding = 'utf-8'
    # noinspection PyTypeChecker
    if hasattr(sys.stdin, 'encoding') and sys.stdin.encoding:
        encoding = sys.stdin.encoding
    if sys.version_info[0] == 2:
        # noinspection PyCompatibility,PyUnresolvedReferences
        result = raw_input(prompt).decode(encoding)
    else:
        result = input(prompt)
    return result


def ensure_dir(dirname, parent=False):
    """ensure that `dirname` exists and is a directory.

    :param dirname:
    :param parent: only check for the parent directory of `dirname`
    :return:
    """
    if parent:
        dirname = os.path.dirname(dirname)
    if os.path.exists(dirname) and not os.path.isdir(dirname):
        raise IOError('%s exists but is not a directory' % dirname)
    elif os.path.isdir(dirname):
        return
    os.makedirs(dirname)


def import_string(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If the `silent` is True the return value will be `None` if the import
    fails.

    :return: imported object
    """
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            items = import_name.split('.')
            module = '.'.join(items[:-1])
            obj = items[-1]
        else:
            return __import__(import_name)
        return getattr(__import__(module, None, None, [obj]), obj)
    except (ImportError, AttributeError):
        if not silent:
            raise ImportError('Unable to import %s' % import_name)


def before_time_replace(dt, year=None, month=None, day=None, dow=None, hour=None, minute=None, second=None,
                        microsecond=None):
    """Return the given `datetime.datetime` object

    >>> dt = datetime.datetime(2016, 6, 15, 12, 30, 30, 500)
    >>> before_time_replace(dt, day=4) == datetime.datetime(2016, 6, 4, 12, 30, 30, 500)
    True
    >>> before_time_replace(dt, day=25) == datetime.datetime(2016, 5, 25, 12, 30, 30, 500)
    True
    >>> before_time_replace(dt, month=4) == datetime.datetime(2016, 4, 15, 12, 30, 30, 500)
    True
    >>> before_time_replace(dt, month=8) == datetime.datetime(2015, 8, 15, 12, 30, 30, 500)
    True
    >>> before_time_replace(dt, hour=4) == datetime.datetime(2016, 6, 15, 4, 30, 30, 500)
    True
    >>> before_time_replace(dt, hour=15) == datetime.datetime(2016, 6, 14, 15, 30, 30, 500)
    True
    >>> before_time_replace(dt, dow=1) == datetime.datetime(2016, 6, 14, 12, 30, 30, 500)
    True
    >>> before_time_replace(dt, dow=6) == datetime.datetime(2016, 6, 12, 12, 30, 30, 500)
    True

    :param dt: a datetime.datetime instance
    :param year: replace the year
    :param month: replace the month.
    :param day: replace the day (of the month)
    :param dow: replace the day of week (Monday is 0 and Sunday is 6)
    :param hour:
    :param minute:
    :param second:
    :param microsecond:
    :return:
    """
    assert isinstance(dt, datetime.datetime)
    if microsecond is not None:
        offset = -datetime.timedelta(seconds=1) if dt.microsecond < microsecond else datetime.timedelta(0)
        dt = dt.replace(microsecond=microsecond) + offset
    if second is not None:
        offset = -datetime.timedelta(minutes=1) if dt.second < second else datetime.timedelta(0)
        dt = dt.replace(second=second) + offset
    if minute is not None:
        offset = -datetime.timedelta(hours=1) if dt.minute < minute else datetime.timedelta(0)
        dt = dt.replace(minute=minute) + offset
    if hour is not None:
        offset = -datetime.timedelta(days=1) if dt.hour < hour else datetime.timedelta(0)
        dt = dt.replace(hour=hour) + offset
    if day is not None:
        if dt.day > day:
            dt = dt.replace(day=day)
        elif dt.month == 1:
            # noinspection PyTypeChecker
            dt = dt.replace(year=dt.year - 1, month=12, day=day)
        else:
            # noinspection PyTypeChecker
            dt = dt.replace(month=dt.month - 1, day=day)
    if dow is not None:
        if dt.weekday() >= dow:
            dt -= datetime.timedelta(days=(dt.weekday() - dow))
        else:
            dt -= datetime.timedelta(days=(dt.weekday() - dow + 7))
    if month is not None:
        if dt.month < month:
            # noinspection PyTypeChecker
            dt = dt.replace(year=dt.year - 1, month=month)
        else:
            dt = dt.replace(month=month)
    if year is not None:
        dt = dt.replace(year=year)
    return dt


def get_is_time_elapsed(fmt):
    """Return a function `(current_time, previous_time)` that returns:

    True if `previous_time` is None or `current_time - previous_time` is greater than the value `fmt`

    `fmt` is a string, with the following format:

        * "86400": max. number of  seconds
        * "monthly:4": the 4th day of each month
        * "weekly:4": the 4th day of each week
        * "weekly": once a week
        * "daily:4": the 4th hour of each day
        * "daily": once a day

    :param fmt:

    >>> current_time = datetime.datetime(2016, 6, 15, 12, 30, 30, 500)
    >>> get_is_time_elapsed('daily')(current_time, datetime.datetime(2016, 6, 15, 11, 30, 30, 500))
    False
    >>> get_is_time_elapsed('daily')(current_time, datetime.datetime(2016, 6, 14, 11, 30, 30, 500))
    True


    :return:
    """
    if not fmt:
        fmt = ''
    if re.match('^\d+$', fmt):
        # number => number of seconds
        return lambda current_time, previous_time: previous_time is None or \
                                                   (current_time - previous_time).total_seconds() > int(fmt)
    matcher = re.match('^monthly:(\d+)$', fmt)
    if matcher:
        x = int(matcher.group(1))
        return lambda current_time, previous_time: previous_time is None or \
            previous_time < before_time_replace(current_time, day=x)
    matcher = re.match('^weekly:(\d+)$', fmt)
    if matcher:
        x = int(matcher.group(1))
        return lambda current_time, previous_time: previous_time is None or \
            previous_time < before_time_replace(current_time, dow=x)
    elif fmt == 'weekly':
        return lambda current_time, previous_time: previous_time is None or \
                                                   (current_time - previous_time).total_seconds() > 7 * 86400
    matcher = re.match('^daily:(\d+)$', fmt)
    if matcher:
        x = int(matcher.group(1))
        return lambda current_time, previous_time: previous_time is None or \
            previous_time < before_time_replace(current_time, hour=x)
    elif fmt == 'daily':
        return lambda current_time, previous_time: previous_time is None or \
                                                   (current_time - previous_time).total_seconds() > 86400
    return lambda current_time, previous_time: True


# noinspection PyPep8Naming
class cached_property(object):
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(get_absolute_url, name='url') )
    """
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    # noinspection PyUnusedLocal,PyShadowingBuiltins
    def __get__(self, instance, type=None):
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


def copytree(src, dst, symlinks=False):
    """copy all files from the source to the destination using hard links if possible"""
    if src == dst:
        return
    if not os.path.exists(dst):  # required to check the underlying device
        os.makedirs(dst)
    dst_st_dev = os.stat(dst).st_dev
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    elif os.path.exists(dst):
        os.unlink(dst)
    if os.stat(src).st_dev != dst_st_dev:
        shutil.copytree(src, dst, symlinks=symlinks)
        return
    os.makedirs(dst)
    shutil.copystat(src, dst)
    for root, dirnames, filenames in os.walk(src):
        for src_dirname in dirnames:
            src_path = os.path.join(root, src_dirname)
            dst_path = os.path.join(dst, os.path.relpath(src_path, src))
            os.makedirs(dst_path)
            shutil.copystat(src_path, dst_path)
        for src_filename in filenames:
            src_path = os.path.join(root, src_filename)
            dst_path = os.path.join(dst, os.path.relpath(src_path, src))
            if symlinks and os.path.islink(src_path):
                linkto = os.readlink(src_path)
                os.symlink(linkto, dst_path)
            else:
                os.link(src_path, dst_path)
                shutil.copystat(src_path, dst_path)
