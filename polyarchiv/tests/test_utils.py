# coding=utf-8
from __future__ import unicode_literals

import codecs
import os
import shutil
import tempfile
from unittest import TestCase

from polyarchiv.utils import copytree


class TestCopyTree(TestCase):
    def test_copytree(self):
        with tempfile.NamedTemporaryFile() as fd:
            src_dir = fd.name
        with tempfile.NamedTemporaryFile() as fd:
            dst_dir = fd.name
        os.makedirs(src_dir)
        os.makedirs(dst_dir)
        os.makedirs(os.path.join(src_dir, "dir1"))
        with codecs.open(os.path.join(src_dir, "file1"), "w", encoding="utf-8") as fd:
            fd.write("file1")
        path = os.path.join(dst_dir, "file2")
        open(path, "w").close()
        os.chmod(path, 0o400)
        copytree(src_dir, dst_dir)
        shutil.rmtree(src_dir)
        shutil.rmtree(dst_dir)
