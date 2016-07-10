# coding=utf-8
"""Storage backend for two kinds of remote repositories:

    * RollingArchive
    * Synchronize

These backends are based on ssh, webdav, ftp and file

Authentication methods:

    * ssh: username:private_key or username:password
    * webdav: username:password + ca_cert
    * ftp: username:password + ca_cert
    * file: no auth

"""
from __future__ import unicode_literals

import os
import shlex
import shutil
from xml.dom.minidom import parseString

# noinspection PyProtectedMember
from polyarchiv._vendor import requests

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse, urlencode, quote_plus
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urlparse import urlparse
    # noinspection PyUnresolvedReferences
    from urllib import urlencode, quote_plus

DOWNLOAD_CHUNK_SIZE_BYTES = 1 * 1024 * 1024


def get_backend(repository, root_url, keytab=None, private_key=None, ca_cert=None, rsync_executable='rsync',
                curl_executable='curl', scp_executable='scp', ssh_executable='ssh', ssh_options=''):
    """

    :param repository:
    :param root_url:
    :param keytab:
    :param private_key:
    :param ca_cert: `None`, 'any' (no check) or cert path
    :param rsync_executable:
    :param curl_executable:
    :param scp_executable:
    :param ssh_options:
    :param ssh_executable:
    :return:
    """
    # noinspection PyUnusedLocal
    curl_executable = curl_executable
    parsed_url = urlparse(root_url)
    scheme = parsed_url.scheme
    if parsed_url.netloc == '' and scheme == '':  # root_url = "/foo/bar/baz/'
        return FileStorageBackend(repository, parsed_url.path, rsync_executable=rsync_executable)
    elif scheme == 'file':
        return FileStorageBackend(repository, parsed_url.path, rsync_executable=rsync_executable)
    elif scheme in ('http', 'https'):
        url = '%s://%s' % (parsed_url.scheme, parsed_url.hostname)
        if parsed_url.port:
            url += ':%s' % parsed_url.port
        url += parsed_url.path
        query = ''
        if parsed_url.query:
            query = '?%s' % parsed_url.query
        if keytab is None:
            return HTTPRequestsStorageBackend(repository, url, query=query, username=parsed_url.username,
                                              password=parsed_url.password, ca_cert=ca_cert, private_key=private_key)
        # return HTTPCurlStorageBackend(repository, url, query=query, username=parsed_url.username,
        #                               password=parsed_url.password, ca_cert=ca_cert, private_key=private_key,
        #                               keytab=keytab)
    elif scheme == 'ftp':
        pass
    elif scheme == 'ftps':
        pass
    elif scheme == 'ssh':
        return SShStorageBackend(repository, parsed_url.path, hostname=parsed_url.hostname, port=parsed_url.port or 22,
                                 username=parsed_url.username, private_key=private_key,
                                 rsync_executable=rsync_executable, ssh_executable=ssh_executable,
                                 scp_executable=scp_executable, ssh_options=ssh_options)
    raise ValueError('Unknown protocol %s' % root_url)


def force_dirname(path):
    return path if path.endswith('/') else path + '/'


class StorageBackend(object):
    def __init__(self, repository):
        from polyarchiv.repository import Repository
        assert isinstance(repository, Repository)
        self.repository = repository

    def can_execute_command(self, text):
        return self.repository.can_execute_command(text)

    def execute_command(self, cmd, ignore_errors=False, cwd=None, stderr=None, stdout=None, stdin=None, env=None,
                        error_str=None):
        return self.repository.execute_command(cmd, ignore_errors=ignore_errors, cwd=cwd, stderr=stderr,
                                               stdout=stdout, stdin=stdin, env=env, error_str=error_str)

    def ensure_dir(self, dirname, parent=False):
        return self.repository.ensure_dir(dirname, parent=parent)

    def ensure_absent(self, path):
        return self.repository.ensure_absent(path)

    def sync_dir_to_local(self, local_dirname):
        raise NotImplementedError

    def sync_dir_from_local(self, local_dirname):
        raise NotImplementedError

    def sync_file_to_local(self, local_filename, filename=''):
        raise NotImplementedError

    def sync_file_from_local(self, local_filename, filename=''):
        raise NotImplementedError

    def delete_on_distant(self, path=''):
        raise NotImplementedError


class FileStorageBackend(StorageBackend):

    def __init__(self, repository, dst_path, rsync_executable='rsync'):
        super(FileStorageBackend, self).__init__(repository)
        self.rsync_executable = rsync_executable
        self.dst_path = dst_path

    def sync_dir_from_local(self, local_dirname):
        self.ensure_dir(self.dst_path, parent=False)
        self.ensure_dir(local_dirname, parent=False)
        cmd = [self.rsync_executable, '-az', '--delete', '-S', force_dirname(local_dirname),
               force_dirname(self.dst_path)]
        self.execute_command(cmd)

    def sync_dir_to_local(self, local_dirname):
        self.ensure_dir(self.dst_path, parent=False)
        self.ensure_dir(local_dirname, parent=False)
        cmd = [self.rsync_executable, '-az', '--delete', '-S', force_dirname(self.dst_path),
               force_dirname(local_dirname)]
        self.execute_command(cmd)

    def sync_file_to_local(self, local_filename, filename=''):
        dst_path = os.path.join(self.dst_path, filename) if filename else self.dst_path
        self.ensure_dir(local_filename, parent=True)
        self.ensure_absent(local_filename)
        if self.can_execute_command(['cp', '-p', dst_path, local_filename]) and local_filename != dst_path:
            shutil.copy2(dst_path, local_filename)

    def sync_file_from_local(self, local_filename, filename=''):
        dst_path = os.path.join(self.dst_path, filename) if filename else self.dst_path
        if local_filename is None:
            with open(dst_path, 'rb') as fd:
                return fd.read()
        self.ensure_dir(dst_path, parent=True)
        self.ensure_absent(dst_path)
        if self.can_execute_command(['cp', '-p', local_filename, dst_path]) and local_filename != dst_path:
            shutil.copy2(local_filename, dst_path)

    def delete_on_distant(self, path=''):
        dst_path = os.path.join(self.dst_path, path) if path else self.dst_path
        self.ensure_absent(dst_path)


class HTTPRequestsStorageBackend(StorageBackend):

    def __init__(self, repository, root_url, query='', username=None, password=None, ca_cert=None, private_key=None,
                 curl_command='curl', keytab=None):
        super(HTTPRequestsStorageBackend, self).__init__(repository)
        self.query = query
        if root_url.endswith('/'):
            root_url = root_url[:-1]  # ok, the root URL never ends by "/"
        self.root_url = root_url
        self.session = requests.session()
        self.session.verify = True
        self.session.auth = (username or '', password or '') if (username is not None or password is not None) else None
        if ca_cert == 'any':
            self.session.verify = False
        elif ca_cert:
            self.session.verify = ca_cert
        if private_key:
            self.session.cert = private_key
        self.session.stream = True
        self.curl_command = curl_command
        self.keytab = keytab

    def sync_dir_to_local(self, local_dirname):
        for root, dirnames, filenames in self.walk('/'):
            current_local_dir = os.path.join(local_dirname, root[1:])
            paths_to_remove = []
            if self.ensure_dir(current_local_dir):
                paths_to_remove = [x for x in (set(os.listdir(current_local_dir)) - set(dirnames) - set(filenames))]
                paths_to_remove = [os.path.join(current_local_dir, x) for x in paths_to_remove]
                paths_to_remove.sort()
            if paths_to_remove and self.can_execute_command(['rm', '-rf'] + paths_to_remove):
                for path in paths_to_remove:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
            # no need to create directories (they will be the next roots)
            for filename in filenames:
                self.download_file(root + filename, os.path.join(local_dirname, root[1:], filename))

    def sync_dir_from_local(self, local_dirname):
        self.delete_on_distant('')
        self.remote_mkdirs('/')
        for root, dirnames, filenames in os.walk(local_dirname):
            for src_dirname in dirnames:
                src_path = os.path.join(root, src_dirname)
                self.remote_mkdir('/' + os.path.relpath(src_path, local_dirname))
            for src_filename in filenames:
                src_path = os.path.join(root, src_filename)
                self.upload_file('/' + os.path.relpath(src_path, local_dirname), src_path)

    def sync_file_to_local(self, local_filename, filename=''):
        if filename:
            filename = '/' + filename
        self.download_file(filename, local_filename)

    def sync_file_from_local(self, local_filename, filename=''):
        if filename:
            filename = '/' + filename
        self.remote_mkdirs(filename)
        self.upload_file(filename, local_filename)

    def delete_on_distant(self, path=''):
        if path:
            path = '/' + path
        url = self.get_url(path)
        if self.can_execute_command(self.get_curl_command(url, '-X', 'DELETE')):
            self.send('DELETE', (204, 207, 404), url=url, headers={'Depth': 'infinity'})

    def get_url(self, suffix='/'):
        if suffix:
            return '%s%s%s' % (self.root_url, suffix, self.query)
        return self.root_url + self.query

    def get_curl_command(self, url, *extra_args):
        command = [self.curl_command] + list(extra_args)
        if not self.session.verify:
            command += ['-k']
        elif self.session.verify is not True:
            command += ['--cacert', self.session.verify]
        if self.session.cert:
            command += ['--cert', self.session.cert]
        if self.session.auth:
            command += ['-u', '%s:%s' % self.session.auth]
        command += [url]
        return command

    def send(self, method, expected_code, suffix='/', url=None, **kwargs):
        if url is None:
            url = self.get_url(suffix)
        response = self.session.request(method, url, allow_redirects=False, **kwargs)
        if isinstance(expected_code, int) and response.status_code != expected_code \
                or not isinstance(expected_code, int) and response.status_code not in expected_code:
            raise IOError('Unable to perform %s %s (%s)' % (method, url, response.status_code))
        return response

    def remote_mkdir(self, suffix):
        url = self.get_url(suffix)
        if self.can_execute_command(self.get_curl_command(url, '-X', 'MKCOL')):
            self.send('MKCOL', (201, 204, 400, 401, 403, 405), url=url)

    def remote_mkdirs(self, suffix):
        url = self.get_url(suffix=suffix)
        parsed_url = urlparse(url)
        prefix = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
        suffix = ''
        if parsed_url.query:
            suffix += '?%s' % parsed_url.query
        if parsed_url.fragment:
            suffix += '#%s' % parsed_url.fragment
        path = ''
        path_components = [x for x in filter(lambda y: y, parsed_url.path.split('/'))]
        if not url.endswith('/') and path_components:
            del path_components[-1]
        for path_component in path_components:
            path += '/' + path_component
            url = '%s%s%s' % (prefix, path, suffix)
            if self.can_execute_command(self.get_curl_command(url, '-X', 'MKCOL')):
                self.send('MKCOL', (201, 204, 400, 401, 403, 405), url=url)

    def upload_file(self, suffix, local_path):
        url = self.get_url(suffix)
        if self.can_execute_command(self.get_curl_command(url, '-X', 'PUT', '-T', local_path)):
            with open(local_path, 'rb') as fd:
                self.send('PUT', (200, 201, 204), url=url, data=fd)

    def download_file(self, suffix, local_path):
        if os.path.isdir(local_path) and self.can_execute_command(['rm', '-rf'] + local_path):
            shutil.rmtree(local_path)
        self.ensure_dir(local_path, parent=True)
        url = self.get_url(suffix)
        if self.can_execute_command(self.get_curl_command(url, '-O', local_path)):
            response = self.send('GET', 200, url=url, stream=True)
            with open(local_path, 'wb') as fd:
                for chunk in response.iter_content(DOWNLOAD_CHUNK_SIZE_BYTES):
                    fd.write(chunk)

    def walk(self, suffix='/'):
        dirnames, filenames = self.ls(suffix=suffix)
        yield suffix, dirnames, filenames
        for dirname in dirnames:
            for data in self.walk('%s%s/' % (suffix, dirname)):
                yield data

    def ls(self, suffix='/', url=None):
        if url is None:
            url = self.get_url(suffix)
        response = self.send('PROPFIND', (207, 301), url=url, headers={'Depth': '1'})
        if response.status_code == 301:
            return self.ls(url=urlparse(response.headers['location']))
        return self.analyze_propfind(url, response.content)

    @staticmethod
    def analyze_propfind(orig_url, content):
        orig_path = urlparse(orig_url).path
        xml_content = parseString(content)
        dirnames, filenames = [], []
        if orig_path.endswith('/'):
            orig_path = orig_path[:-1]
        for response in xml_content.getElementsByTagName('D:response'):
            href = response.getElementsByTagName('D:href')[0].childNodes[0].data
            path = urlparse(href).path
            if path.endswith('/'):
                path = path[:-1]
            if path == orig_path:
                continue
            elif len(response.getElementsByTagName('D:collection')):
                dirnames.append(path.rpartition('/')[2])
            else:
                filenames.append(path.rpartition('/')[2])
        return dirnames, filenames


class HTTPCurlStorageBackend(HTTPRequestsStorageBackend):

    def get_url(self, suffix='/'):
        if suffix:
            return '%s%s%s' % (self.root_url, suffix, self.query)
        return self.root_url + self.query

    def get_curl_command(self, suffix, *extra_args):
        url = self.get_url(suffix)
        command = [self.curl_command] + list(extra_args)
        if not self.session.verify:
            command += ['-k']
        elif self.session.verify is not True:
            command += ['--cacert', self.session.verify]
        if self.session.cert:
            command += ['--cert', self.session.cert]
        if self.session.auth:
            command += ['-u', '%s:%s' % self.session.auth]
        command += [url]
        return command

    def send(self, method, expected_code, suffix='/', url=None, **kwargs):
        if url is None:
            url = self.get_url(suffix)
        response = self.session.request(method, url, allow_redirects=False, **kwargs)
        if isinstance(expected_code, int) and response.status_code != expected_code \
                or not isinstance(expected_code, int) and response.status_code not in expected_code:
            raise IOError('Unable to perform %s %s (%s)' % (method, url, response.status_code))
        return response

    def sync_dir_to_local(self, local_dirname):
        for root, dirnames, filenames in self.walk('/'):
            current_local_dir = os.path.join(local_dirname, root[1:])
            paths_to_remove = []
            if self.ensure_dir(current_local_dir):
                paths_to_remove = [x for x in (set(os.listdir(current_local_dir)) - set(dirnames) - set(filenames))]
                paths_to_remove = [os.path.join(current_local_dir, x) for x in paths_to_remove]
                paths_to_remove.sort()
            if paths_to_remove and self.can_execute_command(['rm', '-rf'] + paths_to_remove):
                for path in paths_to_remove:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
            for filename in filenames:
                self.download_file(root + filename, os.path.join(local_dirname, root[1:], filename))

    def sync_dir_from_local(self, local_dirname):
        self.delete_on_distant('/')
        for root, dirnames, filenames in os.walk(local_dirname):
            for src_dirname in dirnames:
                src_path = os.path.join(root, src_dirname)
                self.remote_mkdir('/' + os.path.relpath(src_path, local_dirname))
            for src_filename in filenames:
                src_path = os.path.join(root, src_filename)
                self.upload_file('/' + os.path.relpath(src_path, local_dirname), src_path)

    def sync_file_to_local(self, local_filename, filename='/filename'):
        self.download_file('/' + filename, local_filename)

    def sync_file_from_local(self, local_filename, filename='filename'):
        self.upload_file('/' + filename, local_filename)

    def delete_on_distant(self, path=''):
        if self.can_execute_command(self.get_curl_command(path, '-X', 'DELETE')):
            self.send('DELETE', (204, 207, 404), suffix=path, headers={'Depth': 'infinity'})

    def remote_mkdir(self, suffix):
        if self.can_execute_command(self.get_curl_command(suffix, '-X', 'MKCOL')):
            self.send('MKCOL', (201, 204, 400, 401, 403, 405), suffix=suffix)

    def upload_file(self, suffix, local_path):
        if self.can_execute_command(self.get_curl_command(suffix, '-X', 'PUT', '-T', local_path)):
            with open(local_path, 'rb') as fd:
                self.send('PUT', (200, 201, 204), suffix=suffix, data=fd)

    def download_file(self, suffix, local_path):
        if os.path.isdir(local_path) and self.can_execute_command(['rm', '-rf'] + local_path):
            shutil.rmtree(local_path)
        if self.can_execute_command(self.get_curl_command(suffix, '-O', local_path)):
            response = self.send('GET', 200, suffix=suffix, stream=True)
            with open(local_path, 'wb') as fd:
                for chunk in response.iter_content(DOWNLOAD_CHUNK_SIZE_BYTES):
                    fd.write(chunk)

    def walk(self, suffix='/'):
        dirnames, filenames = self.ls(suffix=suffix)
        yield suffix, dirnames, filenames
        for dirname in dirnames:
            for data in self.walk('%s%s/' % (suffix, dirname)):
                yield data

    def ls(self, suffix='/', url=None):
        if url is None:
            url = self.get_url(suffix)
        response = self.send('PROPFIND', (207, 301), url=url, headers={'Depth': '1'})
        if response.status_code == 301:
            return self.ls(url=urlparse(response.headers['location']))
        return self.analyze_propfind(url, response.content)

    @staticmethod
    def analyze_propfind(orig_url, content):
        orig_path = urlparse(orig_url).path
        xml_content = parseString(content)
        dirnames, filenames = [], []
        if orig_path.endswith('/'):
            orig_path = orig_path[:-1]
        for response in xml_content.getElementsByTagName('D:response'):
            href = response.getElementsByTagName('D:href')[0].childNodes[0].data
            path = urlparse(href).path
            if path.endswith('/'):
                path = path[:-1]
            if path == orig_path:
                continue
            elif len(response.getElementsByTagName('D:collection')):
                dirnames.append(path.rpartition('/')[2])
            else:
                filenames.append(path.rpartition('/')[2])
        return dirnames, filenames


class SShStorageBackend(FileStorageBackend):

    def __init__(self, repository, dst_path, hostname=None, port=22, username=None, private_key=None,
                 keytab=None, rsync_executable='rsync', ssh_executable='ssh', scp_executable='scp',
                 ssh_options=None):
        super(SShStorageBackend, self).__init__(repository, dst_path, rsync_executable=rsync_executable)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.keytab = keytab
        self.private_key = private_key
        self.ssh_executable = ssh_executable
        self.scp_executable = scp_executable
        self.ssh_options = ssh_options

    def _get_ssh_command(self, use_keytab=True, executable=None):
        cmd = []
        if use_keytab and self.keytab:
            cmd += ['k5start', '-q', '-f', self.keytab, '-U', '--']
        if executable is None:
            executable = self.ssh_executable
        cmd += [executable]
        if self.private_key:
            cmd += ['-i', self.private_key]
        if self.username:
            cmd += ['-l', self.username]
        if self.port:
            cmd += ['-p', str(self.port)]
        if self.ssh_options:
            cmd += list(shlex.split(self.ssh_options))
        return cmd

    def _get_scp_command(self, use_keytab=True, executable=None):
        cmd = []
        if use_keytab and self.keytab:
            cmd += ['k5start', '-q', '-f', self.keytab, '-U', '--']
        if executable is None:
            executable = self.scp_executable
        cmd += [executable]
        if self.private_key:
            cmd += ['-i', self.private_key]
        if self.username:
            cmd += ['-l', self.username]
        if self.port:
            cmd += ['-P', str(self.port)]
        if self.ssh_options:
            cmd += list(shlex.split(self.ssh_options))
        return cmd

    def _get_rsync_command(self):
        cmd = []
        if self.keytab:
            cmd += ['k5start', '-q', '-f', self.keytab, '-U', '--']
        cmd += [self.rsync_executable]
        cmd += ['-e', ' '.join(self._get_ssh_command(use_keytab=False))]
        return cmd

    def sync_dir_from_local(self, local_dirname):
        cmd = self._get_ssh_command()
        cmd += [self.hostname, 'mkdir', '-p', self.dst_path]
        self.execute_command(cmd)
        self.ensure_dir(local_dirname, parent=False)
        cmd = self._get_rsync_command()
        cmd += ['-az', '--delete', '-S', force_dirname(local_dirname),
                '%s:%s' % (self.hostname, force_dirname(self.dst_path))]
        self.execute_command(cmd)

    def sync_dir_to_local(self, local_dirname):
        cmd = self._get_ssh_command()
        cmd += [self.hostname, 'mkdir', '-p', self.dst_path]
        self.execute_command(cmd)
        self.ensure_dir(local_dirname, parent=False)
        cmd = self._get_rsync_command()
        cmd += ['-az', '--delete', '-S', '%s:%s' % (self.hostname, force_dirname(self.dst_path)),
                force_dirname(local_dirname)]
        self.execute_command(cmd)

    def sync_file_to_local(self, local_filename, filename=''):
        dst_path = os.path.join(self.dst_path, filename) if filename else self.dst_path
        parent_path = os.path.dirname(dst_path)
        cmd = self._get_ssh_command()
        cmd += [self.hostname, 'mkdir', '-p', parent_path]
        self.execute_command(cmd)

        self.ensure_dir(local_filename, parent=True)
        cmd = self._get_scp_command(executable=self.scp_executable)
        cmd += ['-p', '%s:%s' % (self.hostname, self.dst_path), local_filename]
        self.execute_command(cmd)

    def sync_file_from_local(self, local_filename, filename=''):
        dst_path = os.path.join(self.dst_path, filename) if filename else self.dst_path
        self.ensure_dir(dst_path, parent=True)
        cmd = self._get_scp_command(executable=self.scp_executable)
        cmd += ['-p', local_filename, '%s:%s' % (self.hostname, self.dst_path)]
        self.execute_command(cmd)

    def delete_on_distant(self, path=''):
        dst_path = os.path.join(self.dst_path, path) if path else self.dst_path
        cmd = self._get_ssh_command()
        cmd += [self.hostname, 'rm', '-rf', dst_path]
        self.execute_command(cmd)
