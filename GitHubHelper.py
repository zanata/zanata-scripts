#!/usr/bin/env python
"""GitHub Helper functions
Run GitHubHelper.py --help or JenkinsHelper.py --help <command> for
detail help."""

import argparse
import json
import logging
import os
import re
import sys
import urllib2  # noqa: F401 # pylint: disable=import-error,unused-import

from urllib import quote_plus
from ZanataFunctions import UrlHelper, logging_init

try:
    # We need to import 'List' and 'Any' for mypy to work
    from typing import List, Any  # noqa: F401 # pylint: disable=unused-import
except ImportError:
    sys.stderr.write("python typing module is not installed" + os.linesep)


class GitHubHelper(UrlHelper):
    """GitHub Helper functions"""
    @staticmethod
    def auth_field_token_function(user, password):
        # type (str, str) -> dict
        """Generate Basic auth header field"""
        return {'Authorization': "token %s:%s" % (user, password)}

    def __init__(self, user, password):
        # type: (str, str) -> None
        self.api_server = 'api.github.com'
        super(GitHubHelper, self).__init__(
                'https://' + self.api_server, user, password,
                GitHubHelper.auth_field_token_function,
                )

    def __getitem__(self, key):
        # type: (str) -> str
        return self[key]

    @staticmethod
    def init_default():
        # type: () -> None
        """Init GitHub connection with default environment."""
        user = os.environ.get('ZANATA_GITHUB_USER')
        token = os.environ.get('ZANATA_GITHUB_TOKEN')

        if not user:
            raise AssertionError("Missing environment 'ZANATA_GITHUB_USER'")
        if not token:
            raise AssertionError("Missing environment 'ZANATA_GITHUB_TOKEN'")

        return GitHubHelper(user, token)

    @staticmethod
    def create_parent_parser():
        # type () -> argparse.ArgumentParser
        """Create a parser as parent of argument parser"""
        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument(
                'repo_name', type=str, help='repository name')
        parent_parser.add_argument('tag', type=str, help='git tag')
        return parent_parser

    def has_tag(self, repo_name, tag):
        # type: (str, str) -> bool
        """Whether the repo_name has tag"""
        try:
            self.request(
                    "/repos/zanata/%s/git/refs/tags/%s" % (repo_name, tag))
            return True
        except urllib2.HTTPError, e:
            if e.code == 404:
                return False
            raise e
        except urllib2.URLError, e:
            raise e

    def create_release(  # pylint: disable=too-many-arguments
            self, repo_name, tag, draft=True, prerelease=False, body=''):
        # type: (str, str, bool, bool, str) -> object
        """Create Release"""
        data_str = '{"tag_name": "%s",\n' % tag
        if body:
            data_str += ' "body": "%s",\n' % body
        data_str += ' "draft": %s,\n' % (draft and 'true' or 'false')
        data_str += ' "prerelease": %s}' % (prerelease and 'true' or 'false')

        headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'}
        response = self.request(
                "/repos/zanata/%s/releases" % repo_name,
                data_str, headers,
                "create_release")
        if response.code >= 200 and response.code < 300:
            logging.info("Code %s: Release creation OK", response.code)
            return response
        else:
            raise Exception(
                    "Code=%d Reason=%s" % (response.code, response.reason))

    def obtain_release_upload_url(  # pylint: disable=too-many-arguments,
            self, repo_name, tag, draft=True, prerelease=False, body=''):
        # type: (str, str, bool, bool, str) -> url
        """Obtain the URL for uploading
        draft: (bool) create a draft release
        prerelase: (bool) this release is a prerelease (e.g. alpha, rc)
        body: (str) body text for release
        """
        try:
            response = self.request(
                    "/repos/zanata/%s/releases/tags/%s" % (repo_name, tag))
        except urllib2.HTTPError, e:
            if e.code == 404:
                logging.info("No release under tag %s", tag)
                response = self.create_release(
                        repo_name, tag,
                        draft=draft, prerelease=prerelease, body=body)
            else:
                raise e
        except urllib2.URLError, e:
            raise e
        parsed_res = json.loads(response.info)
        return parsed_res['upload_url']

    def upload(  # pylint: disable=too-many-arguments,
            self, repo_name, tag, source_file,
            label='',
            draft=True, prerelease=False, body=''):
        # type: (str, str, str, str, bool, bool, str) -> None
        """Upload file to associated tag/release"""
        raw_upload_url = self.obtain_release_upload_url(
                repo_name, tag, draft, prerelease, body)
        upload_url = re.sub(
                "^(http.*/releases/[0-9]+/assets).*$", "\\1",
                raw_upload_url)
        url = "%s?name=%s" % (
                upload_url,
                quote_plus(os.path.basename(source_file)))
        if label:
            url += "&label=%s" % quote_plus(label)
        UrlHelper.upload_file_curl(url, source_file, self.user, self.password)


def has_tag():
    # type () -> None
    """Whether repo_name has tag """
    gh = GitHubHelper.init_default()
    if gh.has_tag(args.repo_name, args.tag):
        print "yes"
    else:
        print "no"


def upload():
    # type () -> None
    """Upload file to a release.
    Will create a new release if the release does not exist yet."""
    gh = GitHubHelper.init_default()
    gh.upload(
            args.repo_name, args.tag, args.source_file,
            draft=args.draft, prerelease=args.prerelease)


def parse():
    # type () -> None
    """Parse options and arguments"""

    parser = argparse.ArgumentParser(description=GitHubHelper.__doc__)
    parent_parser = GitHubHelper.create_parent_parser()

    subparsers = parser.add_subparsers(
            title='Command', description='Valid commands',
            help='Command help')

    has_tag_parser = subparsers.add_parser(
            'has-tag',
            help=has_tag.__doc__,
            parents=[parent_parser],
            )
    has_tag_parser.set_defaults(func=has_tag)

    upload_parser = subparsers.add_parser(
            'upload',
            help=upload.__doc__,
            parents=[parent_parser],
            )
    upload_parser.add_argument(
            '-d', '--draft', action='store_true',
            default=False, help='Create draft release')

    upload_parser.add_argument(
            '-p', '--prerelease', action='store_true',
            default=False, help='Create pre-release')

    upload_parser.add_argument(
            'source_file', type=str, help='File to be upload')
    upload_parser.set_defaults(
            func=upload)
    return parser.parse_args()


if __name__ == '__main__':
    logging_init()

    args = parse()  # pylint: disable=invalid-name
    args.func()
