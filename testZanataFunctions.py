#!/usr/bin/env python
"""Test the ZanataFunctions"""

from __future__ import (
        absolute_import, division, print_function, unicode_literals)

import subprocess  # nosec
import unittest
import ZanataFunctions


class ZanataFunctionsTestCase(unittest.TestCase):
    """Test Case for ZanataFunctions"""
    def test_read_env(self):
        """Test read_env()"""
        zanata_env = ZanataFunctions.read_env(
                ZanataFunctions.ZANATA_ENV_FILE)
        self.assertEqual(zanata_env['EXIT_OK'], '0')


class SshHostTestCase(unittest.TestCase):
    """Test SSH with localhost
    thus set up password less SSH is required"""
    def setUp(self):
        self.ssh_host = ZanataFunctions.SshHost('localhost')

    def test_run_check_call(self):
        """Test SssHost.run_check_call"""
        self.ssh_host.run_check_call('true')
        self.assertRaises(
                subprocess.CalledProcessError,
                self.ssh_host.run_check_call,
                'false')


if __name__ == '__main__':
    unittest.main()
