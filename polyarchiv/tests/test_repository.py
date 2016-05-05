# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase
import datetime
from polyarchiv.repository import RepositoryInfo

__author__ = 'Matthieu Gallet'


class TestRepository(TestCase):

    def test_info(self):
        now = datetime.datetime.now()
        now = now.replace(microsecond=0)
        r1 = RepositoryInfo(last_fail=now, last_message="message", last_state_valid=True, last_success=now,
                            success_count=10, fail_count=10, total_size=42)
        as_dict = r1.to_dict()
        r2 = RepositoryInfo.from_dict(as_dict)
        for k in r1.__dict__:
            self.assertEqual(getattr(r1, k), getattr(r2, k))
        as_str = r1.to_str()
        r3 = RepositoryInfo.from_str(as_str)
        for k in r1.__dict__:
            self.assertEqual(getattr(r1, k), getattr(r3, k))
