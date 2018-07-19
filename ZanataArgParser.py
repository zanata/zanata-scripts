#!/usr/bin/env python
"""ZanataArgParser is an sub-class of ArgumentParser
that handles sub-parser, environments more easily."""

from __future__ import (
        absolute_import, division, print_function)

from argparse import ArgumentParser, ArgumentError
import logging
import os


class ZanataArgParser(ArgumentParser):
    """Zanata Argument Parser"""
    def __init__(self, *args, **kwargs):
        # type: (str, object, object) -> None
        super(ZanataArgParser, self).__init__(*args, **kwargs)
        self.sub_parsers = None
        self.env_def = {}
        self.parent_parser = ArgumentParser(add_help=False)
        self.add_argument(
                '-v', '--verbose', type=str, default='INFO',
                metavar='VERBOSE_LEVEL',
                help='Valid values: %s'
                % 'DEBUG, INFO, WARNING, ERROR, CRITICAL, NONE')

    def add_common_argument(self, *args, **kwargs):
        # type:  (str, object, object) -> argparse
        """Add a common argument that will be used in all sub commands
        In other words, common argument wil be put in common parser.
        Note that add_common_argument must be put in then front of
        add_sub_command that uses common arguments."""
        self.parent_parser.add_argument(*args, **kwargs)

    def add_sub_command(self, name, arguments, **kwargs):
        # type:  (str, object, object) -> argparse ArgumentParser
        """Add a sub command"""
        if not self.sub_parsers:
            self.sub_parsers = self.add_subparsers(
                    title='Command', description='Valid commands',
                    help='Command help')

        if 'parents' in kwargs:
            kwargs['parents'] += [self.parent_parser]
        else:
            kwargs['parents'] = [self.parent_parser]

        anonymous_parser = self.sub_parsers.add_parser(
                name, **kwargs)
        if arguments:
            for k, v in arguments.iteritems():
                anonymous_parser.add_argument(*k.split(), **v)
        anonymous_parser.set_defaults(sub_command=name)
        return anonymous_parser

    def add_env(  # pylint: disable=too-many-arguments
            self, env_name,
            default=None,
            required=False,
            value_type=str,
            dest=None,
            sub_commands=None):
        # type: (str, object, bool, type, str, List[str]) -> None
        """Add environment variable
            env_name: Environment variable name
            default: Default value
            value_type: type of value e.g. str
            dest: attribute name to be return by parse_*
            sub_commands: List of subcommands that use this environment"""
        if not dest:
            dest = env_name.lower()
        if env_name in self.env_def:
            raise ArgumentError(
                    None, "Duplicate environment name %s" % env_name)
        self.env_def[env_name] = {
                'default': default,
                'required': required,
                'value_type': value_type,
                'dest': dest,
                'sub_commands': sub_commands}

    def has_common_argument(self, option_string=None, dest=None):
        # type: (str, str) -> bool
        """Has the parser defined this argument as a common argument?
           Either specify option_string or dest
           option_string: option in command line. e.g. -i
           dest: attribute name to be return by parse_*"""
        for action in self.parent_parser._actions:  # pylint: disable=W0212
            if option_string:
                if option_string in action.option_strings:
                    return True
                else:
                    continue
            elif dest:
                if dest == action.dest:
                    return True
                else:
                    continue
            else:
                raise ArgumentError(None, "need either option_string or dest")
        return False

    def has_env(self, env_name):
        # type: (str) -> bool
        """Whether this parser parses this environment"""
        return env_name in self.env_def

    def parse_args(self, args=None, namespace=None):
        # type: (str, List, object) -> argparse.Namespace
        """Parse arguments"""
        result = super(ZanataArgParser, self).parse_args(args, namespace)
        logging.basicConfig(
                format='%(asctime)-15s [%(levelname)s] %(message)s')
        logger = logging.getLogger()
        if result.verbose == 'NONE':
            # Not showing any log
            logger.setLevel(logging.CRITICAL + 1)
        elif hasattr(logging, result.verbose):
            logger.setLevel(getattr(logging, result.verbose))
        else:
            ArgumentError(None, "Invalid verbose level: %s" % result.verbose)
        delattr(result, 'verbose')
        return result

    @staticmethod
    def _is_env_valid(env_name, env_value, env_data, args):
        # type (str, str, dict, argparse.Namespace) -> bool
        """The invalid env should be skipped or raise error"""
        # Skip when the env is NOT in the list of supported sub-commands
        if env_data['sub_commands'] and args and hasattr(args, 'sub_command'):
            if args.sub_command not in env_data['sub_commands']:
                return False

        # Check whether the env_value is valid
        if not env_value:
            if env_data['required']:
                # missing required value
                raise AssertionError("Missing environment '%s'" % env_name)
            elif not env_data['default']:
                # no default value
                return False
        return True

    def parse_env(self, args=None):
        # type: (argparse.Namespace) -> dict
        """Parse environment"""
        result = {}
        for env_name in self.env_def:
            env_data = self.env_def[env_name]
            env_value = os.environ.get(env_name)
            try:
                if not ZanataArgParser._is_env_valid(
                        env_name, env_value, env_data, args):
                    continue
            except AssertionError as e:
                raise e
            if not env_value:
                if env_data['required']:
                    raise AssertionError("Missing environment '%s'" % env_name)
                elif not env_data['default']:
                    continue
                else:
                    env_value = env_data['default']
            result[env_data['dest']] = env_value
        return result

    def parse_all(self, args=None, namespace=None):
        # type: (str, List, object) -> argparse.Namespace
        """Parse arguments and environment"""
        result = self.parse_args(args, namespace)
        env_dict = self.parse_env(result)
        for k, v in env_dict.iteritems():  # pylint: disable=no-member
            setattr(result, k, v)
        return result
