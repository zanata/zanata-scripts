#!/usr/bin/env python
"""Test the ZanataArgParser.py"""

from __future__ import (
        absolute_import, division, print_function)

import StringIO  # pylint: disable=E0401
import os
import sys
import unittest
import ZanataArgParser  # pylint: disable=E0401


def _convert_unicode_str(dictionary):
    """Recursively converts dictionary keys to strings"""
    if not isinstance(dictionary, dict):
        if isinstance(dictionary, unicode):    # NOQA  # pylint: disable=E0602
            return str(dictionary)
        return str(dictionary)
    return dict(
            (str(k), _convert_unicode_str(v))
            for k, v in dictionary.iteritems())


class ZanataArgParserTestCase(unittest.TestCase):
    """Test Case for ZanataArgParser.py"""
    def setUp(self):
        self.parser = ZanataArgParser.ZanataArgParser('parser-test')
        self.parser.add_common_argument(
                '-b', '--branch', type=str, default='',
                help='branch or PR name')
        self.parser.add_common_argument('job_name', type=str, help='job name')
        self.parser.add_env(
                'HOME', default='str', required=True)
        self.parser.add_env(
                'LOGNAME', default='str', required=False)
        self.parser.add_sub_command(
                'show-job', None, help='Get Job objects')

    def _match_result(
            self, method, expected_args, param_list, stdout_pattern=None):
        captured_output = StringIO.StringIO()
        sys.stdout = captured_output
        args = getattr(self.parser, method)(param_list)
        sys.stdout = sys.__stdout__
        if stdout_pattern:
            self.assertRegexpMatches(  # pylint: disable=W1505
                    captured_output.getvalue(), stdout_pattern)
        self.assertDictEqual(
                _convert_unicode_str(expected_args),
                _convert_unicode_str(args.__dict__))

    def test_add_sub_command(self):
        """Test add_sub_command"""
        self.parser.add_sub_command(
                'show-last-successful-build',
                {'-F --folder': {
                        'type': str, 'default': '',
                        'help': 'folder name'}},
                help='Get build objects')

        # Test Run
        self._match_result(
                'parse_args',
                {
                        'branch': '',
                        'job_name': 'zanata-platform',
                        'sub_command': 'show-job'},
                ['show-job', 'zanata-platform'])
        self._match_result(
                'parse_args',
                {
                        'branch': '', 'folder': 'github-zanata-org',
                        'job_name': 'zanata-platform',
                        'sub_command': 'show-last-successful-build'},
                [
                        'show-last-successful-build',
                        '-F', 'github-zanata-org', 'zanata-platform'])

    def test_env(self):
        """Test parse_env"""
        home = os.environ.get('HOME')
        env_dict = self.parser.parse_env()
        self.assertEqual(home, env_dict['home'])

    def test_parse_all(self):
        """Test parse_all"""
        log_name = os.environ.get('LOGNAME')
        home = os.environ.get('HOME')

        self._match_result(
                'parse_all',
                {
                        'branch': 'release',
                        'job_name': 'zanata-platform',
                        'sub_command': 'show-job',
                        'home': home,
                        'logname': log_name},
                [
                        'show-job',
                        '-b', 'release', 'zanata-platform'])

        env_dict = self.parser.parse_env()
        self.assertEqual(home, env_dict['home'])


if __name__ == '__main__':
    unittest.main()
