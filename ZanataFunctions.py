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
    """Read environment variables by sourcing a bash file

    Args:
        filename (str): Bash file to be read

    Returns:
        [dict]: Dict whose key is environment variable name,
            and value is variable value.

    Examples:
    >>> read_env('zanata-env.sh')['EXIT_OK']
    u'0'
    """
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
    WORK_ROOT = str(os.environ.get('WORK_ROOT'))
elif ZANATA_ENV['WORK_ROOT']:
    WORK_ROOT = str(ZANATA_ENV['WORK_ROOT'])
else:
    WORK_ROOT = os.getcwd()


def exec_call(cmd_list, **kwargs):
    # type (List[str], Any) -> int
    """Run command and return exit status

    This function runs, the command described by cmd_list,
    wait for command to complete, then return the exit status.

    Args:
        cmd_list (List[str]): Command and arguments to be run.
        **kwargs: subprocess.Popen() keyword arguments

    Returns:
        int: exit status of command.
    """
    logging.debug("Running command: %s", " ".join(cmd_list))
    return subprocess.call(cmd_list, **kwargs)  # nosec


def exec_check_call(cmd_list, **kwargs):
    # type (List[str], Any) -> int
    """Run command and check exit status

    This function runs the command described by cmd_list,
    wait for command to complete, then check the exit status.

    If success (exit status is 0), returns stdout of command;
    otherwise raise subprocess.CalledProcessError()

    Args:
        cmd_list (List[str]): Command and arguments to be run.
        **kwargs: subprocess.Popen() keyword arguments

    Returns:
        int: exit status of command.

    Raises:
        CalledProcessError: When command exit status is not 0
    """
    logging.debug("Running command: %s", " ".join(cmd_list))
    try:
        return subprocess.check_call(cmd_list, **kwargs)  # nosec
    except subprocess.CalledProcessError as e:
        raise e


def exec_check_output(cmd_list, **kwargs):
    # type (List[str], Any) -> str
    """Run command, check exit status then returns stdout as string

    This function runs the command described by cmd_list,
    wait for command to complete, then check the exit status.

    If success (exit status is 0), returns stdout of command,right white spaces
    stripped;
    otherwise raise subprocess.CalledProcessError()

    Args:
        cmd_list (List[str]): Command and arguments to be run.
        **kwargs: subprocess.Popen() keyword arguments

    Returns:
        str: right stripped stdout of command.

    Raises:
        CalledProcessError: When command exit status is not 0
    """
    logging.debug("Running command: %s", " ".join(cmd_list))
    try:
        return subprocess.check_output(cmd_list, **kwargs).rstrip()  # nosec
    except subprocess.CalledProcessError as e:
        raise e


class CLIException(Exception):
    """Exception from command line"""

    def __init__(self, msg, level='ERROR'):
        super(CLIException, self).__init__(type(self))
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

        parsed = urlparse.urlsplit(url)
        data = list(parsed)

        # replace if user is specify
        if user:
            userrec = user
            if token:
                userrec += ":" + token
            netloc = "%s@%s" % (userrec, parsed.hostname)
            data[1] = netloc

        self.url = url
        self.auth_url = urlparse.urlunparse(data)
        self.remote = remote

    @classmethod
    def init_from_parsed_args(cls, args):
        """Init from command line arguments"""
        kwargs = {}
        for k in ['user', 'token', 'url', 'remote']:
            if hasattr(args, k):
                kwargs[k] = getattr(args, k)
        return cls(**kwargs)

    @staticmethod
    def git_check_output(arg_list, **kwargs):
        """Run git command and return stdout as string

        This is just a wrapper of run_check_output()

        Arguments:
            arg_list {LIST[str]} -- git argument lists.

        Keyword Arguments:
            kwarg {Namespace} -- keyword args for subprocess.check_output

        Returns:
            str -- stdout output
        """
        cmd_list = [GitHelper.GIT_CMD] + arg_list
        return exec_check_output(cmd_list, **kwargs)

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
    RSYNC_CMD = '/usr/bin/rsync'
    RSYNC_OPTIONS = [
            '--cvs-exclude', '--recursive', '--verbose', '--links',
            '--update', '--compress', '--exclude', '*.core', '--stats',
            '--progress', '--archive', '--keep-dirlinks']

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
        for k in ['ssh_user', 'identity_file']:
            if hasattr(args, k):
                kwargs[k] = getattr(args, k)
        return cls(**kwargs)

    def _obtain_cmd_list(self, command, sudo):
        # type (str, bool) -> List[str]
        """Return cmd_list"""
        cmd_list = [SshHost.SSH_CMD]
        cmd_list += self.opt_list
        cmd_list += [self.user_host]
        cmd_list += [('sudo ' if sudo else '') + command]
        return cmd_list

    def run_check_call(self, command, sudo=False):
        # type (str, bool) -> None
        """Check the command run through ssh

        Args:
            command (str): Command to be run through ssh
            sudo (bool, optional): Defaults to False. Whether to use 'sudo'

        Returns:
            int: command exit status
        """
        return exec_check_call(self._obtain_cmd_list(command, sudo))

    def run_check_output(self, command, sudo=False):
        # type (str, bool) -> str
        """Check the command run through ssh, and return stdout as string

        Args:
            command (str): Command to be run through ssh
            sudo (bool, optional): Defaults to False. Whether to use 'sudo'

        Returns:
            str: stdout of command
        """
        return exec_check_output(self._obtain_cmd_list(command, sudo))

    def run_chown(self, user, group, filename, options=None):
        # type (str, str, str, List[str]) -> int
        """Run and check chown through ssh

        Args:
            user (str): user of new owner
            group (str): group of new owner
            filename (str): file to be chown
            options (List[str], optional): Defaults to None. chown option list

        Returns:
            int: command exit status
        """
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

        cmd_list = ["/usr/bin/scp", "-p"] + self.opt_list + [
                source_path,
                "%s:%s" % (self.user_host, dest_path)]
        exec_check_call(cmd_list)

    def rsync(self, src, dest, options=None):
        # type (str, str, List[Str]) -> None
        """Run rsync

        Args:
            src (str): src file/dir in rsync
            dest (str): src file/dir in rsync
            options (List[str], optional): Defaults to None.
                    List of rsync options.
        """
        cmd_prefix = [SshHost.RSYNC_CMD] + SshHost.RSYNC_OPTIONS
        if self.ssh_user:
            ssh_cmd = "ssh -l {} {} {}".format(
                    self.ssh_user,
                    "" if not self.identity_file else "-i",
                    "" if not self.identity_file else self.identity_file)
            cmd_prefix += ["-e", ssh_cmd]

        if options:
            cmd_prefix += options
        exec_check_call(cmd_prefix + [src, dest])


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
    """Sort the version from list

    Args:
        version_list (List[str]): version str in a list
        reverse (bool, optional): Defaults to False. Desending sort.

    Returns:
        List[str] -- Sorted list of versions

    Examples:
    >>> version_list = ['1.0.0', '10.0.0', '2.0.0', '1.0.0-rc-1' ]
    >>> version_sort(version_list)
    ['1.0.0-rc-1', '1.0.0', '2.0.0', '10.0.0']
    >>> version_sort(version_list, True)
    ['10.0.0', '2.0.0', '1.0.0', '1.0.0-rc-1']
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


def main():
    """Run as command line program"""
    parser = ZanataArgParser(__file__)
    parser.add_methods_as_sub_commands(GitHelper)
    parser.add_sub_command(
            'module-help', None,
            help='Show Python Module help')
    args = parser.parse_all()

    if args.sub_command == 'module-help':
        help(sys.modules[__name__])
    else:
        parser.run_sub_command(args)


if __name__ == '__main__':
    if os.getenv("PY_DOCTEST", "0") == "1":
        import doctest
        test_result = doctest.testmod()
        print(doctest.testmod(), file=sys.stderr)
        sys.exit(0 if test_result.failed == 0 else 1)
    main()
