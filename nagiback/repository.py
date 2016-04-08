# -*- coding: utf-8 -*-
import json
import datetime
import logging
from nagiback.conf import Parameter
from nagiback.utils import get_is_time_elapsed, text_type

__author__ = 'Matthieu Gallet'
logger = logging.getLogger('nagiback')


class ParameterizedObject(object):
    parameters = []

    def __init__(self, name):
        self.name = name


class RepositoryInfo(object):
    def __init__(self, last_state_valid=None, last_success=None, last_fail=None, success_count=0, fail_count=0,
                 total_size=0, last_message=''):
        self.last_state_valid = last_state_valid  # None, True, False
        self.last_success = last_success  # expected to be filled by datetime.datetime.now()
        self.last_fail = last_fail  # expected to be filled by datetime.datetime.now()
        self.success_count = success_count  # number of successful backups
        self.fail_count = fail_count  # number of failed backups
        self.total_size = total_size  # total size (in bytes) of the backup
        self.last_message = last_message  # should be "ok" for a success, or an informative message on error

    def to_dict(self):
        result = {x: getattr(self, x) for x in ('last_state_valid', 'success_count', 'fail_count', 'total_size',
                                                'last_message')}
        result['last_success'] = None
        result['last_fail'] = None
        if isinstance(self.last_success, datetime.datetime):
            result['last_success'] = self.last_success.strftime('%Y-%m-%mT%H:%M:%S')
        if isinstance(self.last_fail, datetime.datetime):
            result['last_fail'] = self.last_fail.strftime('%Y-%m-%mT%H:%M:%S')
        return result

    @classmethod
    def from_dict(cls, data):
        kwargs = {}
        for k in 'success_count', 'fail_count', 'total_size':
            kwargs[k] = data.get(k, 0)
            assert isinstance(kwargs[k], int)
        kwargs['last_message'] = data.get('last_message', '')
        assert isinstance(kwargs['last_message'], text_type)
        for k in 'last_state_valid':
            kwargs[k] = data.get(k)
            assert kwargs[k] is None or isinstance(kwargs[k], bool)
        return RepositoryInfo(**kwargs)

    def to_str(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_str(cls, text):
        return cls.from_dict(json.loads(text))


class Repository(ParameterizedObject):
    parameters = ParameterizedObject.parameters + [
        Parameter('check_out_of_date_backup', 'frequency', converter=get_is_time_elapsed),
    ]

    def __init__(self, name, check_out_of_date_backup=None, ):
        super(Repository, self).__init__(name)
        self.check_out_of_date_backup = check_out_of_date_backup or get_is_time_elapsed(None)
