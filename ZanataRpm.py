#!/usr/bin/env python2
# encoding: utf-8
"""
ZanataRpm -- RPM manipulate

ZanataRpm mainpulates RPM and spec files,
such as version bump.

It defines classes_and_methods

@author:    Ding-Yi Chen

@copyright:  2018 Red Hat Asia Pacific. All rights reserved.

@license:    LGPLv2+

@contact:    dchen@redhat.com
"""
from __future__ import absolute_import, division, print_function

import datetime
import locale
import logging
import re
import os
import sys

from ZanataArgParser import ZanataArgParser  # pylint: disable=import-error
from ZanataFunctions import CLIException

try:
    from typing import List, Any  # noqa: F401 # pylint: disable=unused-import
except ImportError:
    sys.stderr.write("python typing module is not installed" + os.linesep)

locale.setlocale(locale.LC_ALL, 'C')


class RpmSpec(object):
    """
    RPM Spec
    """

    # We only interested in these tags
    TAGS = ['Name', 'Version', 'Release']

    def __init__(self, **kwargs):
        # type (Any) -> None
        """
        Constructor
        """
        for v in kwargs:
            setattr(self, v, kwargs.get(v))
        self.content = []

    def parse_spec_tag(self, line):
        # type (str) -> None
        """Parse the tag value from line if the line looks like
        spec tag definition, otherwise do nothing"""

        s = line.rstrip()

        matched = re.match(r"([A-Z][A-Za-z]*):\s*(.+)", s)
        if matched:
            if matched.group(1) in RpmSpec.TAGS:

                tag = matched.group(1)
                if not hasattr(self, tag):
                    # Only use the first match
                    setattr(self, tag, matched .group(2))
        return s

    @classmethod
    def init_from_file(cls, spec_file):
        # type (str) -> None
        """Init from existing spec file

        Args:
            spec_file (str): RPM spec file

        Raises:
            OSError e: File error

        Returns:
            RpmSpec: Instance read from spec_file
        """
        try:
            with open(spec_file, 'r') as in_file:
                self = cls()
                self.content = [
                        self.parse_spec_tag(l)
                        for l in in_file.readlines()]
        except OSError as e:
            raise e
        return self

    def update_version(self, version):
        # type (str) -> bool
        """Update to new version

        Args:
            version (str): new version to be set
        """
        if getattr(self, 'Version') == version:
            logging.warning("Spec file is already with version %s", version)
            return False

        setattr(self, 'Version', version)

        # Update content
        new_content = []
        for line in self.content:
            matched = re.match(r"^Version:(\s*)(.+)", line)
            if matched:
                new_content.append(
                        "Version:{}{}".format(matched.group(1), version))
                continue

            changelog_matched = re.match("^%changelog", line)
            if changelog_matched:
                now = datetime.datetime.now().strftime("%a %b %d %Y")
                changelog_item = (
                        "* {date} {email} {version}-1\n"
                        "- Upgrade to upstream version {version}\n".format(
                                date=now,
                                email=os.getenv(
                                        'MAINTAINER_EMAIL',
                                        'noreply@zanata.org'),
                                version=version))
                new_content.append(line)
                new_content.append(changelog_item)
                continue

            new_content.append(line)

        setattr(self, 'content', new_content)
        return True

    def write_to_file(self, spec_file):
        """Write the spec to file

        Args:
            spec_file (str): RPM spec file

        Raises:
            OSError e: File error
        """
        try:
            with open(spec_file, 'w') as out_file:
                out_file.write(str(self))

        except OSError as e:
            logging.error("Failed to write to %s", spec_file)
            raise e

    def __str__(self):
        return "\n".join(getattr(self, 'content'))


def _parse():
    parser = ZanataArgParser(__file__)
    parser.add_sub_command(
            'update-version',
            [
                    ('--force -f', {
                            'action': 'store_true',
                            'help': 'Force overwritten'}),
                    ('spec_file', {
                            'type': str,
                            'help': 'spec file'}),
                    ('version', {
                            'type': str,
                            'help': 'new version'})],
            help=RpmSpec.__doc__)
    return parser.parse_all()


def main():
    """Run as command line program"""
    args = _parse()
    if args.sub_command == 'help':
        help(sys.modules[__name__])
    else:
        if args.sub_command == 'update-version':
            instance = RpmSpec.init_from_file(args.spec_file)
            instance.update_version(args.version)
            instance.write_to_file(args.spec_file)
        else:
            raise CLIException("No known sub command %s" % args.sub_command)


if __name__ == '__main__':
    main()
