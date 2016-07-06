# coding=utf-8
from __future__ import unicode_literals

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse, urlencode, quote_plus
except ImportError:
    # noinspection PyCompatibility, PyUnresolvedReferences
    from urlparse import urlparse
    # noinspection PyUnresolvedReferences
    from urllib import urlencode, quote_plus


def gitlab_projectname(value):
    left, sep, right = value.partition('/')
    if sep != '/':
        raise ValueError('project name must be of the form \'namespace/project\'')
    if '/' in left or '/' in right:
        raise ValueError('project name must be of the form \'namespace/project\'')


def check_git_url(remote_url):
    """Check if the given URL starts by a valid scheme

    >>> check_git_url("http://localhost/tmp.git") == 'http://localhost/tmp.git'
    True

    """
    parsed_url = urlparse(remote_url)
    if parsed_url.scheme and parsed_url.scheme not in ('http', 'https', 'file'):
        raise ValueError('Invalid scheme for remote URL: %s' % parsed_url.scheme)
    return remote_url


def check_curl_url(remote_url):
    """Check if the given URL starts by a valid scheme

    >>> check_curl_url("scp://localhost/tmp") == 'scp://localhost/tmp'
    True

    """
    parsed_url = urlparse(remote_url)
    if parsed_url.scheme not in ('http', 'https', 'scp', 'ftp', 'ftps', 'sftp', 'smb', 'smbs', 'file'):
        raise ValueError('Invalid scheme for remote URL: %s' % parsed_url.scheme)
    return remote_url


def check_archive(value):
    if value.endswith('.tar.gz'):
        return value
    elif value.endswith('.tar.bz2'):
        return value
    elif value.endswith('.tar.xz'):
        return value
    raise ValueError('Archive name must end by .tar.gz, .tar.bz2 or .tar.xz')
