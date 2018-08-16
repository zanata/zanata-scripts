#!/usr/bin/env python
"""Generic Helper Function"""

from __future__ import (absolute_import, division, print_function)

import codecs
import errno
import logging
import os
import re
import subprocess  # nosec
import sys
import urllib2  # noqa: F401 # pylint: disable=import-error
import urlparse  # noqa: F401 # pylint: disable=import-error

from contextlib import contextmanager
from distutils.version import LooseVersion
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
if 'WORK_ROOT' in os.environ:
    WORK_ROOT = os.getenv('WORK_ROOT')
elif ZANATA_ENV['WORK_ROOT']:
    WORK_ROOT = ZANATA_ENV['WORK_ROOT']
else:
    WORK_ROOT = os.getcwd


class CLIException(Exception):
    """Exception from command line"""

    def __init__(self, msg, level='ERROR'):
        super(CLIException).__init__(type(self))
        self.msg = "[%s] %s" % (level, msg)

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class GitHelper(object):
    """Git Helper functions"""
    GIT_CMD = '/usr/bin/git'

    def __init__(
            self, user=None, token=None,
            url='https://github.com/zanata/zanata-platform.git',
            remote='origin'):
        # type: (str, str, str, str) -> None
        self.user = user
        self.token = token
        url_parsed = urlparse.urlparse(url)
        if user:
            url_parsed.username = user
        if token:
            url_parsed.password = token

        self.url = url
        self.auth_url = urlparse.urlunparse(url_parsed)
        self.remote = remote

    @staticmethod
    def git_check_output(arg_list, **kwargs):
        """Run git command and return stdout as string

        This is just a wrapper of subprocess.check_output()

        Arguments:
            arg_list {LIST[str]} -- git argument lists.

        Keyword Arguments:
            kwarg {Namespace} -- keyword args for subprocess.check_output

        Returns:
            str -- stdout output
        """
        cmd_list = [GitHelper.GIT_CMD] + arg_list
        logging.debug("Running command: %s", " ".join(cmd_list))
        return subprocess.check_output(cmd_list, **kwargs)

    @staticmethod
    def branch_get_current():
        # type () -> str
        """Return current branch name, or HEAD when detach."""
        return GitHelper.git_check_output([
                'rev-parse', '--abbrev-ref', 'HEAD'])

    def branch_forced_pull(self, branch=None, remote=None):
        # type (str, str, str) -> None
        """Withdraw local changes and pull the remote,
        which, by default, is self.remote or 'origin'
        Note that function does nothing to a detached HEAD"""
        if not branch:
            branch = self.branch_get_current()
        if branch == 'HEAD':
            return None
        if not remote:
            remote = self.remote if self.remote else 'origin'
        msg = self.git_check_output(
                ['fetch', remote, branch])
        logging.info(msg)
        msg = self.git_check_output([
                'reset', '--hard',
                "{}/{}".format(remote, branch)])
        logging.info(msg)

    @staticmethod
    def detect_remote_repo_latest_version(
            tag_prefix='', remote_repo='.'):
        # type (str, str) -> str
        """Get the latest version from remote repo without clone the whole repo

        Known Bug: "latest version" does not mean version of latest tag,
        but just the biggest version.

        For example, if you tag v2.0, then tag v1.8.
        The returned verion will be v2.0

        Keyword Arguments:
            tag_prefix {str} -- prefix of a tag to be strip (default: {''})
            remote_repo {str} -- the remote git repo, can be URL, repo name,
                    '.' for local repository,
                    or None to use the self.url (default: {None})

        Returns:
            str -- the latest version
        """
        lines = GitHelper.git_check_output([
                'ls-remote', '--tags', remote_repo,
                'refs/tags/%s*[^^{{}}]' % tag_prefix]).strip().split('\n')
        index = len('refs/tags/%s' % tag_prefix)
        versions = version_sort([l.split()[1][index:] for l in lines], True)
        return versions[0]


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

        # Produce [user@]hostname
        self.user_host = "%s%s" % (
                '' if not self.ssh_user else self.ssh_user + '@', self.host)

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

    def _run_check(self, command, sudo):
        # type (str, bool) -> List[str]
        """Return cmd_list"""
        cmd_list = [SshHost.SSH_CMD]
        cmd_list += self.opt_list
        cmd_list += [self.user_host]
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
                "%s:%s" % (self.user_host, dest_path)]

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


def mkdir_p(directory, mode=0o755):
    # type(str) -> None
    """Ensure the directory and intermediate directories exists,
    just like mkdir -p"""
    try:
        os.makedirs(directory, mode)
        logging.info("Directory %s created", directory)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(directory):
            raise


def version_sort(version_list, reverse=False):
    """Sort the version

    Arguments:
        version_list {List[str]} -- List of versions

    Keyword Arguments:
        reverse {bool} -- Whether to reverse sort (default: {False})

    Returns:
        List[str] -- Sorted list of versions
    """
    # Add -zfinal to final releases, so it can be sorted after rc
    sorted_dirty_version = sorted(
            [re.sub(
                    '^([.0-9]+)$', r'\1-zfinal', v) for v in version_list],
            key=LooseVersion, reverse=reverse)

    return [re.sub('-zfinal', '', v) for v in sorted_dirty_version]


@contextmanager
def working_directory(directory):
    # type(str) -> None
    """Context manager for change directory
    Usage: with working_directory('~'):
           ..."""
    curr_directory = os.getcwd()
    try:
        logging.debug("cd to %s", directory)
        mkdir_p(directory)
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(curr_directory)


def _parse():
    parser = ZanataArgParser(__file__)
    parser.add_sub_command(
            'list-run', None,
            help='list runable functions')
    parser.add_sub_command(
            'run',
            [
                    ('func_name', {
                            'type': str, 'default': '',
                            'help': 'Function name'}),
                    ('func_args', {
                            'type': str,
                            'nargs': '*',
                            'help': 'Function arguments'})],
            help='Run function')
    parser.add_sub_command(
            'module-help', None,
            help='Show Python Module help')
    return parser.parse_all()


def _run_as_cli():
    import inspect
    args = _parse()
    if args.sub_command == 'module-help':
        help(sys.modules[__name__])
    elif args.sub_command == 'list-run':
        cmd_list = inspect.getmembers(GitHelper, predicate=inspect.ismethod)
        for cmd in cmd_list:
            if cmd[0][0] == '_':
                continue
            print("%s:\n       %s\n" % (cmd[0], cmd[1].__doc__))
            print(inspect.getargspec(cmd[1]))
    elif args.sub_command == 'run':
        if hasattr(GitHelper, args.func_name):
            g_helper = GitHelper()
            print(getattr(g_helper, args.func_name)(*args.func_args))
        else:
            raise CLIException("No known func name %s" % args.func_name)


if __name__ == '__main__':
    _run_as_cli()
