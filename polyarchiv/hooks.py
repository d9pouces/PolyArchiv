# coding=utf-8
from __future__ import unicode_literals

import os
import shlex
import smtplib
from email.mime.text import MIMEText

# noinspection PyProtectedMember
from polyarchiv._vendor import requests
# noinspection PyProtectedMember
from polyarchiv._vendor.requests.auth import HTTPBasicAuth
from polyarchiv.conf import Parameter, strip_split, CheckOption
from polyarchiv.points import ParameterizedObject
from polyarchiv.utils import text_type, FileContentMonitor, DEFAULT_EMAIL


class Hook(ParameterizedObject):
    parameters = ParameterizedObject.parameters + [
        Parameter('events', converter=strip_split, required=True,
                  help_str='list of events (comma-separated) that trigger this hook: "before_backup",'
                           '"backup_success", "backup_error", "after_backup".'),
    ]
    keep_output = True

    def __init__(self, name, runner, parameterized_object, events=None, **kwargs):
        super(Hook, self).__init__(name, **kwargs)
        assert isinstance(parameterized_object, ParameterizedObject)
        self.runner = runner
        self.parameterized_object = parameterized_object
        self.hooked_events = set(events)

    def stderr(self):
        return self.runner.stderr

    def stdout(self):
        return self.runner.stdout

    def print_message(self, *args, **kwargs):
        return self.runner.print_message(*args, **kwargs)

    def call(self, when, cm, collect_point_results, backup_point_results):
        assert isinstance(when, text_type)
        assert isinstance(cm, FileContentMonitor)
        assert isinstance(collect_point_results, dict)  # dict[collect_point.name] = True/False
        assert isinstance(backup_point_results, dict)  # dict[(backup_point.name, collect_point.name)] = True/False
        raise NotImplementedError

    def set_extra_variables(self, cm, collect_point_results, backup_point_results):
        self.variables.update(self.parameterized_object.variables)
        assert isinstance(cm, FileContentMonitor)
        content = cm.get_text_content()
        if not collect_point_results and not backup_point_results:
            self.variables['status'] = '--'
        elif all(collect_point_results.values()) and all(backup_point_results.values()):
            self.variables['status'] = 'OK'
        else:
            self.variables['status'] = 'KO'
        text_values = {True: 'OK', False: 'KO'}
        detailed_status = ['%s: %s' % (text_values[key], key) for key in sorted(collect_point_results)]
        detailed_status += ['%s: %s on %s' % (text_values[key], key[0], key[1]) for key in sorted(backup_point_results)]
        self.variables.update({'complete_log': content, 'detailed_status': '\n'.join(detailed_status)})


class LogHook(Hook):
    """store PolyArchiv's output to the given path. Be sure to set `keep_output` to `y`."""
    parameters = Hook.parameters + [
        Parameter('path', required=True,
                  help_str='path of the log file [*]'),
    ]

    def __init__(self, name, runner, path=None, **kwargs):
        super(LogHook, self).__init__(name, runner, **kwargs)
        self.path = path

    def call(self, when, cm, collect_point_results, backup_point_results):
        assert isinstance(cm, FileContentMonitor)
        path = self.format_value(self.path)
        with open(path, 'wb') as fd:
            cm.copy_content(fd, close=False)


class EmailHook(Hook):
    """Send an email to one or more recipient when the hook is called.
    Some extra variables are available:

        * "status" ('--' for "before_backup" hooks, 'OK' or 'KO' otherwise) ,
        * "detailed_status" (one 'KO'/'OK' per line, for each backup or collect point, empty for "before_backup" hooks)
        * "complete_log" (the complete stdout log).
    """
    default_content = "{detailed_status}\n\n{complete_log}"
    default_subject = "[BACKUP][{fqdn}] {Y}/{m}/{d} {H}:{M} [{status}]"
    parameters = Hook.parameters + [
        Parameter('recipient', required=True, help_str='recipients, separated by commas [*]'),
        Parameter('subject', help_str='subject (default to "%s") [*]' % default_subject),
        Parameter('content', help_str='mail content (default to "%s") [*]' % default_content),
        Parameter('sender', help_str='from address (default to %s) [*]' % DEFAULT_EMAIL),
        Parameter('hostname', help_str='SMTP server name (default to "localhost")'),
        Parameter('port', help_str='SMTP server port', converter=int),
        Parameter('username', help_str='SMTP client username'),
        Parameter('password', help_str='SMTP client password'),
        Parameter('keyfile', help_str='client PEM key file'),
        Parameter('certfile', help_str='client PEM cert file'),
        Parameter('encryption', help_str='Encryption method ("none", "starttls" or "tls")',
                  converter=CheckOption(["none", "starttls", "tls"])),
    ]

    def __init__(self, name, runner, recipient='', subject=default_subject, content=default_content,
                 sender=DEFAULT_EMAIL, hostname='localhost', port=0, username=None, password=None, keyfile=None,
                 certfile=None, encryption="none", **kwargs):
        super(EmailHook, self).__init__(name, runner, **kwargs)
        self.recipient = recipient
        self.subject = subject
        self.content = content
        self.sender = sender
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.keyfile = keyfile
        self.certfile = certfile
        self.encryption = encryption

    def call(self, when, cm, collect_point_results, backup_point_results):
        self.set_extra_variables(cm, collect_point_results, backup_point_results)
        msg = MIMEText(self.format_value(self.content))
        # me == the sender's email address
        # you == the recipient's email address
        msg['Subject'] = self.format_value(self.subject)
        msg['From'] = self.format_value(self.sender)
        msg['To'] = self.format_value(self.recipient)

        # Send the message via our own SMTP server.
        if self.encryption == "tls":
            smtp = smtplib.SMTP_SSL(host=self.hostname, port=self.port, keyfile=self.keyfile, certfile=self.certfile)
        else:
            smtp = smtplib.SMTP(host=self.hostname, port=self.port)
        if self.encryption == 'starttls':
            smtp.starttls(keyfile=self.keyfile, certfile=self.certfile)
        if self.username and self.password:
            smtp.login(self.username, self.password)
        smtp.send_message(msg)
        smtp.quit()


class HttpHook(Hook):
    """Perform a HTTP request.

    """
    default_body = ''
    parameters = Hook.parameters + [
        Parameter('url', required=True, help_str='requested URL [*]'),
        Parameter('method', help_str='HTTP method (default to "GET")'),
        Parameter('body', help_str='request body (empty by default) [*]'),
        Parameter('username', help_str='HTTP username [*]'),
        Parameter('password', help_str='HTTP password [*]'),
        Parameter('keyfile', help_str='client PEM key file [*]'),
        Parameter('certfile', help_str='client PEM cert file [*]'),
        Parameter('cafile', help_str='CA cert PEM file, or "ignore" to ignore invalid certificates [*]'),
        Parameter('proxy_url', help_str='Proxy URL [*]'),
        Parameter('headers', help_str='custom headers, space-separated, e.g. HEADER1=VALUE HEADER2="VA LUE"'),
    ]

    def __init__(self, name, runner, url='', method='GET', body=default_body,
                 username=None, password=None, keyfile=None,
                 certfile=None, cafile=None, proxy_url=None, headers='', **kwargs):
        super(HttpHook, self).__init__(name, runner, **kwargs)
        self.url = url
        self.method = method
        self.body = body
        self.username = username
        self.password = password
        self.keyfile = keyfile
        self.certfile = certfile
        self.cafile = cafile
        self.proxy_url = proxy_url
        self.headers = headers

    def call(self, when, cm, collect_point_results, backup_point_results):
        self.set_extra_variables(cm, collect_point_results, backup_point_results)
        kwargs = {}
        body = self.format_value(self.body)
        if body:
            kwargs['data'] = body
        keyfile, certfile = self.format_value(self.keyfile), self.format_value(self.certfile)
        if keyfile and certfile:
            kwargs['cert'] = (certfile, keyfile)
        cafile = self.format_value(self.cafile)
        if cafile == 'ignore':
            kwargs['verify'] = False
        elif cafile and os.path.isfile(cafile):
            kwargs['verify'] = cafile
        else:
            kwargs['verify'] = True
        proxy_url = self.format_value(self.proxy_url)
        if proxy_url:
            kwargs['proxy'] = {'http': proxy_url, 'https': proxy_url}
        username = self.format_value(self.username)
        password = self.format_value(self.password)
        if username and password:
            kwargs['auth'] = HTTPBasicAuth(username, password)
        headers = {}
        for splitted in shlex.split(self.format_value(self.headers)):
            header_name, sep, header_value = splitted.partition('=')
            if sep == '=':
                headers[header_name] = header_value
        if headers:
            kwargs['headers'] = headers
        url = self.format_value(self.url)
        req = requests.request(self.method, url, **kwargs)
        if req.status_code < 300:
            self.print_error('Request %s returned a %d code' % (url, req.status_code))
        req.close()
