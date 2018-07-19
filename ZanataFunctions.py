#!/usr/bin/env python
"""Generic Helper Function"""

from __future__ import (
        absolute_import, division, print_function, unicode_literals)

import codecs
import errno
import logging
import os
import subprocess  # nosec
import sys
import urllib2  # noqa: F401 # pylint: disable=import-error
import urlparse  # noqa: F401 # pylint: disable=import-error
from ZanataArgParser import ZanataArgParser  # pylint: disable=import-error

try:
    from typing import List, Any  # noqa: F401 # pylint: disable=unused-import
except ImportError:
    sys.stderr.write("python typing module is not installed" + os.linesep)


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ZANATA_ENV_FILE = os.path.join(SCRIPT_DIR, 'zanata-env.sh')
BASH_CMD = '/bin/bash'


def read_env(filename):
    # type (str) -> dict
    """Read environment variables by sourcing a bash file"""
    proc = subprocess.Popen(  # nosec
            [BASH_CMD, '-c',
             "source %s && set -o posix && set" % (filename)],
            stdout=subprocess.PIPE)
    return {kv[0]: kv[1] for kv in [
            u.strip().split('=', 1)
            for u in codecs.getreader('utf8')(proc.stdout).readlines()
            if '=' in u]}


ZANATA_ENV = read_env(ZANATA_ENV_FILE)


class HTTPBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
    """Handle Basic Authentication"""
    def http_error_401(  # pylint: disable=too-many-arguments,unused-argument
            self, req, fp, code, msg, headers):
        """retry with basic auth when facing a 401"""
        host = req.get_host()
        realm = None
        return self.retry_http_basic_auth(host, req, realm)

    def http_error_403(  # pylint: disable=too-many-arguments,unused-argument
            self, req, fp, code, msg, hdrs):
        """retry with basic auth when facing a 403"""
        host = req.get_host()
        realm = None
        return self.retry_http_basic_auth(host, req, realm)


class SshHost(object):
    """SSH/SCP helper functions"""

    SCP_CMD = '/usr/bin/scp'
    SSH_CMD = '/usr/bin/ssh'

    def __init__(self, host, ssh_user=None, identity_file=None):
        # type (str, str, str) -> None
        self.host = host
        self.ssh_user = ssh_user
        self.identity_file = identity_file
        if self.identity_file:
            self.opt_list = ['-i', identity_file]
        else:
            self.opt_list = []

    @classmethod
    def add_parser(cls, arg_parser=None):
        # type (ZanataArgParser) -> ZanataArgParser
        """Add SshHost parameters to a parser"""
        if not arg_parser:
            arg_parser = ZanataArgParser(
                    description=cls.__doc__)
        arg_parser.add_common_argument(
                '-u', '--ssh-user', type=str,
                help='Connect SSH/SCP as this user')
        arg_parser.add_common_argument(
                '-i', '--identity-file', type=str,
                help='SSH/SCP ident-files')
        arg_parser.add_common_argument(
                'host', type=str,
                help='host name')
        return arg_parser

    @classmethod
    def init_from_parsed_args(cls, args):
        """Init from command line arguments"""
        kwargs = {'host': args.host}
        for k in ['ssh_user', 'identitity_file']:
            if hasattr(args, k):
                kwargs[k] = getattr(args, k)
        return cls(**kwargs)

    def _get_user_host(self):
        # type () -> str
        """Produce [user@]host"""
        return "%s%s" % (
                '' if not self.ssh_user else self.ssh_user + '@', self.host)

    def _run_check(self, command, sudo):
        # type (str, bool) -> List[str]
        """Return cmd_list"""
        cmd_list = [SshHost.SSH_CMD]
        cmd_list += self.opt_list
        cmd_list += [self._get_user_host()]
        cmd_list += [('sudo ' if sudo else '') + command]
        logging.debug(' '.join(cmd_list))
        return cmd_list

    def run_check_call(self, command, sudo=False):
        # type (str, bool) -> None
        """Run command though ssh"""
        cmd_list = self._run_check(command, sudo)
        subprocess.check_call(cmd_list)  # nosec

    def run_check_output(self, command, sudo=False):
        # type (str, bool) -> str
        """Run command though ssh, return stdout"""
        cmd_list = self._run_check(command, sudo)
        return subprocess.check_output(cmd_list)  # nosec

    def run_chown(self, user, group, filename, options=None):
        # type (str, bool) -> None
        """Run command though ssh"""
        self.run_check_call(
                "chown %s %s:%s %s" % (
                        '' if not options else ' '.join(options),
                        user, group, filename),
                True)

    def scp_to_host(
            self, source_path, dest_path,
            sudo=False, rm_old=False):
        # type (str, str, bool, bool) -> None
        """scp to host"""
        if rm_old:
            self.run_check_call(
                    "rm -fr %s" % dest_path, sudo)

        cmd_list = ['scp', '-p'] + self.opt_list + [
                source_path,
                "%s:%s" % (self._get_user_host(), dest_path)]

        logging.debug(' '.join(cmd_list))

        subprocess.check_call(cmd_list)  # nosec


class UrlHelper(object):
    """URL helper functions"""
    def __init__(self, base_url, user, token):
        """install the authentication handler."""
        self.base_url = base_url
        auth_handler = HTTPBasicAuthHandler()
        auth_handler.add_password(
                realm=None,
                uri=self.base_url,
                user=user,
                passwd=token)
        opener = urllib2.build_opener(auth_handler)
        # install it for all urllib2.urlopen calls
        urllib2.install_opener(opener)

    @staticmethod
    def read(url):
        # type (str) -> str
        """Read URL"""
        logging.debug("Reading from %s", url)
        return urllib2.urlopen(url).read()  # nosec

    @staticmethod
    def download_file(url, dest_file='', download_dir='.'):
        # type (str, str, str) -> None
        """Download file"""
        target_file = dest_file
        if not target_file:
            url_parsed = urlparse.urlparse(url)
            target_file = os.path.basename(url_parsed.path)
        chunk = 128 * 1024  # 128 KiB
        target_dir = os.path.abspath(download_dir)
        target_path = os.path.join(target_dir, target_file)
        try:
            os.makedirs(target_dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(target_dir):
                # Dir already exists
                pass
            else:
                raise

        logging.info("Downloading to %s from %s", target_path, url)
        response = urllib2.urlopen(url)  # nosec
        chunk_count = 0
        with open(target_path, 'wb') as out_file:
            while True:
                buf = response.read(chunk)
                if not buf:
                    break
                out_file.write(buf)
                chunk_count += 1
                if chunk_count % 100 == 0:
                    sys.stderr.write('#')
                    sys.stderr.flush()
                elif chunk_count % 10 == 0:
                    sys.stderr.write('.')
                    sys.stderr.flush()
        return response
