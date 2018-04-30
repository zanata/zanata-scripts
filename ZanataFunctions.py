#!/usr/bin/env python
"""Generic Helper Function"""

import argparse
import errno
import logging
import os
import subprocess  # nosec
import sys
import urllib2  # noqa: F401 # pylint: disable=import-error,unused-import
import urlparse  # noqa: F401 # pylint: disable=import-error,unused-import

try:
    from typing import List, Any  # noqa: F401 # pylint: disable=unused-import
except ImportError:
    sys.stderr.write("python typing module is not installed" + os.linesep)


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ZANATA_ENV_FILE = os.path.join(SCRIPT_DIR, 'zanata-env.sh')
BASH_CMD = '/bin/bash'


def logging_init(level=logging.INFO):
    # type (int) -> logging.Logger
    """Initialize logging"""
    logging.basicConfig(format='%(asctime)-15s [%(levelname)s] %(message)s')
    logger = logging.getLogger()
    logger.setLevel(level)
    return logger


def read_env(filename):
    # type (str) -> dict
    """Read environment variables by sourcing a bash file"""
    proc = subprocess.Popen(  # nosec
            [BASH_CMD, '-c',
             "source %s && set -o posix && set" % (filename)],
            stdout=subprocess.PIPE)
    return {kv[0]: kv[1] for kv in [
            s.strip().split('=', 1)
            for s in proc.stdout.readlines() if '=' in s]}


ZANATA_ENV = read_env(ZANATA_ENV_FILE)


class HTTPBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
    """Handle Basic Authentication"""
    def http_error_401(self, req, fp, code, msg, headers):  # noqa: E501  # pylint: disable=invalid-name,unused-argument,too-many-arguments
        """retry with basic auth when facing a 401"""
        host = req.get_host()
        realm = None
        return self.retry_http_basic_auth(host, req, realm)

    def http_error_403(self, req, fp, code, msg, hdrs):  # noqa: E501  # pylint: disable=invalid-name,unused-argument,too-many-arguments
        """retry with basic auth when facing a 403"""
        host = req.get_host()
        realm = None
        return self.retry_http_basic_auth(host, req, realm)


class SshHost(object):
    """SSH/SCP helper functions"""

    SCP_CMD = '/usr/bin/scp'
    SSH_CMD = '/usr/bin/ssh'

    @staticmethod
    def create_parent_parser():
        # type () -> argparse.ArgumentParser
        """Create parent parser for SSH related program"""
        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument(
                '-i', '--identity-file', type=str,
                help='SSH/SCP indent-files')
        parent_parser.add_argument(
                'host', type=str,
                help='host with/without username,'
                + ' e.g. user@host.example or host.example')
        parent_parser.add_argument(
                '-t', '--dest-path', type=str, help='Destination path')
        return parent_parser

    def __init__(self, host, identity_file=None):
        # type (str, str) -> None
        self.host = host
        self.identity_file = identity_file
        if self.identity_file:
            self.opt_list = ['-i', identity_file]
        else:
            self.opt_list = []

    def run_check_call(self, command, sudo=False):
        # type (str, bool) -> None
        """Run command though ssh"""
        cmd_list = [SshHost.SSH_CMD]
        cmd_list += self.opt_list
        cmd_list += [
                self.host,
                ('sudo ' if sudo else '') + command]
        logging.info(' '.join(cmd_list))

        subprocess.check_call(cmd_list)  # nosec

    def scp_to_remote(
            self, source_path, dest_path,
            sudo=False, rm_old=False):
        # type (str, str, bool, bool) -> None
        """scp to remote host"""
        if rm_old:
            self.run_check_call(
                    "rm -fr %s" % dest_path, sudo)

        cmd_list = [
                'scp', '-p'] + self.opt_list + [
                        source_path,
                        "%s:%s" % (self.host, dest_path)]

        logging.info(' '.join(cmd_list))

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
        logging.info("Reading from %s", url)
        return urllib2.urlopen(url).read()  # nosec

    @staticmethod
    def download_file(url, dest_file='', dest_dir='.'):
        # type (str, str, str) -> None
        """Download file"""
        target_file = dest_file
        if not target_file:
            url_parsed = urlparse.urlparse(url)
            target_file = os.path.basename(url_parsed.path)
        chunk = 128 * 1024  # 128 KiB
        target_dir = os.path.abspath(dest_dir)
        target_path = os.path.join(target_dir, target_file)
        try:
            os.makedirs(target_dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(target_dir):
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
