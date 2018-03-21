#!/usr/bin/env python
"""Jenkins Helper functions
It contains jenkins helper
Run JenkinsHelper --help or JenkinsHelper --help <command> for
detail help."""

from __future__ import (
        absolute_import, division, print_function, unicode_literals)
import ast
import logging
import os
import os.path
import re
import sys

try:
    # We need to import 'List' and 'Any' for mypy to work
    from typing import List, Any  # noqa: F401 # pylint: disable=unused-import
except ImportError:
    sys.stderr.write("python typing module is not installed" + os.linesep)

from ZanataFunctions import UrlHelper
from ZanataArgParser import ZanataArgParser  # pylint: disable=E0401


class JenkinsServer(object):
    """JenkinsServer can connect to a Jenkins server"""
    def __init__(self, server_url, user, token):
        # type: (str, str,str) -> None
        self.url_helper = UrlHelper(
                server_url, user, token)
        self.server_url = server_url
        self.user = user
        self.token = token

    @classmethod
    def add_parser(cls, arg_parser=None, env_sub_commands=None):
        # type: (ZanataArgParser) -> ZanataArgParser
        """Add JenkinsServer parameters to a parser"""
        if not arg_parser:
            arg_parser = ZanataArgParser(description=__doc__)

        # Add env
        arg_parser.add_env(
                'JENKINS_URL', dest='server_url', required=True,
                sub_commands=env_sub_commands)
        arg_parser.add_env(
                'ZANATA_JENKINS_USER', dest='user', required=True,
                sub_commands=env_sub_commands)
        arg_parser.add_env(
                'ZANATA_JENKINS_TOKEN', dest='token', required=True,
                sub_commands=env_sub_commands)
        return arg_parser

    @classmethod
    def init_from_parsed_args(cls, args):
        """New an instance from parsed args"""
        return cls(args.server_url, args.user, args.token)


class JenkinsJob(object):
    """JenkinsJob object can access a Jenkins Job"""

    @staticmethod
    def dict_get_elem_by_path(dic, path):
        # type (dict, str) -> object
        """Return the elem in python dictionary given path
        for example: you can use a/b to retrieve answer from following
        dict:
            { 'a': { 'b': 'answer' }}"""
        obj = dic
        for key in path.split('/'):
            if obj[key]:
                obj = obj[key]
            else:
                return None
        return obj

    @staticmethod
    def print_key_value(key, value):
        # type (str, str) -> None
        """Pretty print the key and value"""
        return "%30s : %s" % (key, value)

    def get_elem(self, path):
        # type: (str) -> object
        """Get element from the job object"""
        return JenkinsJob.dict_get_elem_by_path(self.content, path)

    def __repr__(self):
        # type: () -> str
        result = "\n".join([
                JenkinsJob.print_key_value(tup[0], tup[1]) for tup in [
                        ['job_name', self.job_name],
                        ['folder', self.folder],
                        ['branch', self.branch]]])
        if self.content:
            result += "\n\n%s" % "\n".join([
                    JenkinsJob.print_key_value(
                            key, self.get_elem(key)) for key in [
                                    'displayName',
                                    'fullName',
                                    'lastBuild/number',
                                    'lastCompletedBuild/number',
                                    'lastFailedBuild/number',
                                    'lastSuccessfulBuild/number']])
        return result

    def __init__(self, server, job_name, folder='', branch=''):
        # type (JenkinsServer, str, str, str) -> None
        self.server = server
        self.job_name = job_name
        self.folder = folder
        self.branch = branch
        self.content = None
        job_path = "job/%s" % self.job_name
        if folder:
            job_path = "job/%s/%s" % (folder, job_path)
        if branch:
            job_path += "/job/%s" % branch
        self.url = "%s%s" % (self.server.server_url, job_path)

    @classmethod
    def add_parser(
            cls, arg_parser=None,
            only_options=False, env_sub_commands=None):
        # type: (ZanataArgParser, bool) -> ZanataArgParser
        """Add JenkinsJob parameters to parser
        arg_parser: existing parser to be appended to
        only_options: Add only options and JenkinsServer env"""
        if not arg_parser or not arg_parser.has_env('JENKINS_URL'):
            arg_parser = JenkinsServer.add_parser(
                    arg_parser, env_sub_commands)
        arg_parser.add_common_argument(
                '-b', '--branch', type=str,
                help='branch or PR name')
        arg_parser.add_common_argument(
                '-F', '--folder', type=str,
                help='GitHub Organization Folder')
        if not only_options:
            arg_parser.add_common_argument(
                    'job_name', type=str, help='job name')

            # Add sub commands
            arg_parser.add_sub_command(
                    'get-job', None,
                    help='Show job objects')
            arg_parser.add_sub_command(
                    'get-last-successful-build', None,
                    help=cls.get_last_successful_build.__doc__)
            arg_parser.add_sub_command(
                    'get-last-successful-artifacts',
                    {
                            '-p --artifact-path-patterns': {
                                    'type': str, 'default': '.*',
                                    'help': 'comma split artifact path regex pattern'}},  # noqa: E501,  #pylint: disable=line-too-long
                    help='Get matching last-successful artifacts. Default: .*')
            arg_parser.add_sub_command(
                    'download-last-successful-artifacts',
                    {
                            '-p --artifact-path-patterns': {
                                    'type': str, 'default': '.*',
                                    'help': 'comma split artifact path regex'
                                    },
                            '-d --download-dir': {
                                    'type': str, 'default': '.',
                                    'help': 'Download directory'}
                            },
                    help='Get matching last-successful artifacts. Default: .*')
        return arg_parser

    @classmethod
    def init_from_parsed_args(cls, args):
        """New an instance from parsed args"""
        server = JenkinsServer.init_from_parsed_args(args)
        kwargs = {'job_name': args.job_name}
        for k in ['folder', 'branch']:
            if hasattr(args, k):
                kwargs[k] = getattr(args, k)
        return cls(server, **kwargs)

    def load(self):
        # type: () -> None
        """Load the build object from Jenkins server"""
        logging.debug("Loading job from %s/api/python", self.url)
        self.content = ast.literal_eval(UrlHelper.read(
                "%s/api/python" % self.url))

    def get_last_successful_build(self):
        # type: () -> JenkinsJobBuild
        """Get last successful build"""
        if not self.content:
            self.load()

        if not self.content:
            raise AssertionError("Failed to load job from %s" % self.url)
        return JenkinsJobBuild(
                self,
                int(self.get_elem('lastSuccessfulBuild/number')),
                self.get_elem('lastSuccessfulBuild/url'))

    def get_last_successful_artifacts(
            self, artifact_path_patterns=None):
        # type: (List[str]) -> List[str]
        """Get last successful artifacts that matches patterns"""
        build = self.get_last_successful_build()
        return build.list_artifacts_related_paths(artifact_path_patterns)

    def download_last_successful_artifacts(
            self, artifact_path_patterns=None, download_dir='.'):
        # type: (List[str])-> List[str]
        """Download last successful artifacts that matches patterns.
        Returns related path of artifacts

        Note the directory structure will be flattern."""
        if not artifact_path_patterns:
            artifact_path_patterns = ['.*']
        build = self.get_last_successful_build()
        artifact_path_list = build.list_artifacts_related_paths(
                artifact_path_patterns)
        for artifact_path in artifact_path_list:
            UrlHelper.download_file(
                    build.url + 'artifact/' + artifact_path,
                    download_dir=download_dir)
        return artifact_path_list


class JenkinsJobBuild(object):
    """Build object for Jenkins job"""

    def __init__(self, parent_job, build_number, build_url):
        # type (object, int, str) -> None
        self.parent_job = parent_job
        self.number = build_number
        self.url = build_url
        self.content = None

    def get_elem(self, path):
        # type: (str) -> object
        """Get element from the build object"""
        return JenkinsJob.dict_get_elem_by_path(self.content, path)

    def load(self):
        """Load the build object from Jenkins server"""
        logging.debug("Loading build from %sapi/python", self.url)
        self.content = ast.literal_eval(UrlHelper.read(
                "%s/api/python" % self.url))

    def list_artifacts_related_paths(self, artifact_path_patterns=None):
        # type: (str) -> List[str]
        """Return a List of relativePaths of artifacts
        that matches the path patterns"""
        if not artifact_path_patterns:
            artifact_path_patterns = ['.*']
        if not self.content:
            self.load()
        if not self.content:
            raise AssertionError("Failed to load build from %s" % self.url)
        result = []
        for artifact in self.content['artifacts']:
            for pattern in artifact_path_patterns:
                if re.search(pattern, artifact['relativePath']):
                    result.append(artifact['relativePath'])
                    break  # Only append once
        return result

    def __repr__(self):
        # type: () -> str
        result = "\n".join([
                JenkinsJob.print_key_value(
                        tup[0], str(tup[1])) for tup in [
                                ['number', self.number],
                                ['url', self.url]]])

        if self.content:
            result += "\n\n%s" % "\n".join([
                    JenkinsJob.print_key_value(
                            key, self.get_elem(key)) for key in [
                                    'nextBuild/number',
                                    'previousBuild/number']])
            result += "\n\nArtifacts:\n%s" % "\n  ".join(
                    self.list_artifacts_related_paths())
        return result


def run_sub_command(args):
    # type (ZanataArgParser.Namespace) -> None
    """Run the sub command"""
    job = JenkinsJob.init_from_parsed_args(args)
    job.load()
    if args.sub_command == 'get-job':
        print(job)
    elif args.sub_command == 'get-last-successful-build':
        build = job.get_last_successful_build()
        build.load()
        print(build)
    elif args.sub_command == 'get-last-successful-artifacts':
        print('\n'.join(
                job.get_last_successful_artifacts(
                        args.artifact_path_patterns.split(','))
                ))
    elif args.sub_command == 'download-last-successful-artifacts':
        artifact_path_list = job.download_last_successful_artifacts(
                args.artifact_path_patterns.split(','),
                args.download_dir)
        print("Downloaded files %s" % '\n'.join(artifact_path_list))


if __name__ == '__main__':
    run_sub_command(JenkinsJob.add_parser().parse_all())
