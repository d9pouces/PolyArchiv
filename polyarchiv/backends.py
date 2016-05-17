# coding=utf-8
"""Storage backend for two kinds of remote repositories:

    * archive
    * synchronize

These backends are based on ssh, webdav, ftp and file

Authentication methods:

    * ssh: username:private_key or username:password
    * webdav: username:password + ca_cert
    * ftp: username:password + ca_cert
    * file: no auth

"""


class StorageBackend(object):
    def __init__(self, root):
        self.root = root
