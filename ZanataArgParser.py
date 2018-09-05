#!/usr/bin/env python
"""ZanataArgParser is an sub-class of ArgumentParser
that handles sub-parser, environments more easily.

This also handles logging with color format.
The color formattting part is borrowed from KurtJacobson's colored_log.py

https://gist.github.com/KurtJacobson/c87425ad8db411c73c6359933e5db9f9"""

from __future__ import (absolute_import, division, print_function)

import inspect
import logging
import os
import re
import sys

from argparse import ArgumentParser, ArgumentError, RawDescriptionHelpFormatter
# Following are for mypy
from argparse import Action  # noqa: F401 # pylint: disable=W0611
from argparse import Namespace  # noqa: F401 # pylint: disable=W0611
from argparse import _SubParsersAction  # noqa: F401 # pylint: disable=W0611

try:
    from typing import List, Any  # noqa: F401 # pylint: disable=W0611
    from typing import Dict  # noqa: F401 # pylint: disable=W0611
    from typing import Optional  # noqa: F401 # pylint: disable=W0611
    from typing import Tuple  # noqa: F401 # pylint: disable=W0611
except ImportError:
    sys.stderr.write("python typing module is not installed" + os.linesep)


class NoSuchMethodError(Exception):
    """Method does not exist

    Args:
        method_name (str): Name of the method
    """
    def __init__(self, method_name):
        super(NoSuchMethodError, self).__init__()
        self.method_name = method_name

    def __str__(self):
        return "No such method: %s" % self.method_name


class ColoredFormatter(logging.Formatter):
    """Log colored formated
    Inspired from KurtJacobson's colored_log.py"""
    # Background ASCII color
    bg = os.getenv("LOGGING_BG_COLOR", 40)  # Default black background

    COLOR_MAPPING = {
            'DEBUG': [os.getenv("LOGGING_DEBUG_COLOR", 37), bg],  # white
            'INFO': [os.getenv("LOGGING_INFO_COLOR", 36), bg],  # cyan
            'WARNING': [os.getenv("LOGGING_WARNING_COLOR", 33), bg],  # yellow
            'ERROR': [os.getenv("LOGGING_ERROR_COLOR", 31), bg],  # red
            'CRITICAL': [37, 41]}  # white on red bg

    PREFIX = '\033['
    SUFFIX = '\033[0m'

    def __init__(self, patern):
        logging.Formatter.__init__(self, patern)

    @staticmethod
    def _color(colors, content):
        if os.getenv("LOGGING_NO_COLOR", ""):
            return ""
        return "\033[%d;%dm%s\033[0m" % (colors[0], colors[1], content)

    def format(self, record):
        if not os.getenv('LOGGING_NO_COLOR', ''):
            # Turn of color with env LOGGING_NO_COLOR=1
            colors = ColoredFormatter.COLOR_MAPPING.get(
                    record.levelname, ColoredFormatter.COLOR_MAPPING['DEBUG'])
            record.levelname = ColoredFormatter._color(
                    colors, record.levelname)
            record.message = ColoredFormatter._color(
                    colors, record.getMessage())
            if self.usesTime():
                record.asctime = ColoredFormatter._color(
                        colors, self.formatTime(record, self.datefmt))
        try:
            s = self._fmt % record.__dict__
        except UnicodeDecodeError as e:
            # Issue 25664. The logger name may be Unicode. Try again ...
            try:
                record.name = record.name.decode('utf-8')
                s = self._fmt % record.__dict__
            except UnicodeDecodeError:
                raise e
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            try:
                s = s + record.exc_text
            except UnicodeError:
                # Sometimes filenames have non-ASCII chars, which can lead
                # to errors when s is Unicode and record.exc_text is str
                # See issue 8924.
                # We also use replace for when there are multiple
                # encodings, e.g. UTF-8 for the filesystem and latin-1
                # for a script. See issue 13232.
                s = s + record.exc_text.decode(sys.getfilesystemencoding(),
                                               'replace')
        return s


class ZanataArgParser(ArgumentParser):
    """Zanata Argument Parser that support sub-commands and environment

    Examples:
    >>> import ZanataArgParser
    >>> parser = ZanataArgParser.ZanataArgParser('my-prog')
    >>> parser.add_common_argument('-b', '--branch', default='master')
    >>> parser.add_sub_command('list', None, None)
    >>> args = parser.parse_all(['list', '-b', 'release'])
    >>> print(args.sub_command)
    list
    >>> print(args.branch)
    release
    >>> args2 = parser.parse_all(['list'])
    >>> print(args2.branch)
    master
    """

    def __init__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        # Ignore mypy "ArgumentParser" gets multiple values for keyword
        # argument "formatter_class"
        # See https://github.com/python/mypy/issues/1028
        super(ZanataArgParser, self).__init__(
                *args, formatter_class=RawDescriptionHelpFormatter, **kwargs)
        self.env_def = {}  # type: Dict[str, dict]
        self.parent_parser = ArgumentParser(add_help=False)
        self.add_argument(
                '-v', '--verbose', type=str, default='INFO',
                metavar='VERBOSE_LEVEL',
                help='Valid values: %s'
                % 'DEBUG, INFO, WARNING, ERROR, CRITICAL, NONE')

        self.sub_parsers = None  # type: _SubParsersAction
        self.sub_command_obj_dict = {}  # type: Dict[str, Any]

    def add_common_argument(self, *args, **kwargs):
        # type:  (Any, Any) -> None
        """Add a common argument that will be used in all sub commands
        In other words, common argument will be put in common parser.
        Note that add_common_argument must be put in then front of
        add_sub_command that uses common arguments."""
        self.parent_parser.add_argument(*args, **kwargs)

    def add_sub_command(self, name, arguments, obj=None, **kwargs):
        # type:  (str, List, Any, Any) -> None
        """Add a sub command

        Args:
            name (str): name of the sub-command
            arguments (dict): argments to be passed to argparse.add_argument()
            obj (Any, optional): Defaults to None. The sub_command is
                a method of the obj.
            kwargs (Any, optional): other arguments for add_parser
        """
        if not self.sub_parsers:
            self.sub_parsers = self.add_subparsers(
                    title='Command', description='Valid commands',
                    help='Command help')

        if obj:
            self.sub_command_obj_dict[name] = obj

        if 'parents' in kwargs:
            kwargs['parents'] += [self.parent_parser]
        else:
            kwargs['parents'] = [self.parent_parser]

        anonymous_parser = self.sub_parsers.add_parser(
                name, **kwargs)
        if arguments:
            for arg in arguments:
                k = arg[0]
                v = arg[1]
                if v:
                    anonymous_parser.add_argument(*k.split(), **v)
                else:
                    anonymous_parser.add_argument(*k.split())
        anonymous_parser.set_defaults(sub_command=name)

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

    def add_methods_as_sub_commands(self, obj, name_pattern='.*'):
        # type (Any, str) -> None
        """Add public methods as sub-commands

        Args:
            cls ([type]): Public methods of obj will be used
            name_pattern (str, optional): Defaults to '.*'.
                    Method name should match the pattern.
        """
        method_list = inspect.getmembers(obj)
        for m in method_list:
            if not re.match(name_pattern, m[0]):
                continue

            name = m[0]
            m_obj = m[1]

            if name[0] == '_':
                # No private functions (which start with _)
                continue

            if not inspect.ismethod(m_obj) and not inspect.isfunction(m_obj):
                continue

            if name == 'init_from_parsed_args':
                # init_from_parsed_args initialize from parsed args.
                # No need to be in sub-commands
                continue

            argspec = inspect.getargspec(m_obj)
            sub_args = None
            try:
                start_idx = len(argspec.args) - len(argspec.defaults)
            except TypeError:
                start_idx = len(argspec.args) + 1
            for idx, a in enumerate(argspec.args):
                if a == 'self' or a == 'cls':
                    continue
                if argspec.defaults and idx >= start_idx:
                    arg_def = {
                            'nargs': '?',
                            'default': argspec.defaults[idx - start_idx]}
                else:
                    arg_def = None
                if sub_args:
                    sub_args.append(tuple([a, arg_def]))
                else:
                    sub_args = [tuple([a, arg_def])]

            self.add_sub_command(
                    name,
                    sub_args,
                    obj,
                    help=re.sub(
                            "\n.*$", "", m_obj.__doc__, flags=re.MULTILINE),
                    description=m_obj.__doc__)

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

    @staticmethod
    def set_logger(verbose):
        # type: (str) -> None
        """Handle logger
        Inspired from KurtJacobson's colored_log.py"""
        # Root logger will be fine
        logger = logging.getLogger()
        # Add console handler
        s_handler = logging.StreamHandler()
        s_handler.setLevel(logging.DEBUG)
        c_formatter = ColoredFormatter(
                '%(asctime)-15s [%(levelname)s] %(message)s')
        s_handler.setFormatter(c_formatter)
        logger.addHandler(s_handler)
        if verbose == 'NONE':
            # Not showing any log
            logger.setLevel(logging.CRITICAL + 1)
        elif hasattr(logging, verbose):
            logger.setLevel(getattr(logging, verbose))
        else:
            ArgumentError(None, "Invalid verbose level: %s" % verbose)

    def parse_args(self, args=None, namespace=None):
        # type: (Any, Any) -> Namespace
        """Parse arguments"""
        result = super(ZanataArgParser, self).parse_args(args, namespace)
        ZanataArgParser.set_logger(result.verbose)

        # We do not need verbose for the caller
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
        # type: (Namespace) -> dict
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
        # type: (List, Namespace) -> Namespace
        """Parse arguments and environment"""
        result = self.parse_args(args, namespace)
        env_dict = self.parse_env(result)
        for k, v in env_dict.iteritems():  # pylint: disable=no-member
            setattr(result, k, v)
        return result

    def run_sub_command(self, args=None):
        """Run the sub ccommand with parsed arguments

        Args:
            instance ([type]): [description]
            args ([type], optional): Defaults to None. Arguments

        Raises:
            ArgumentError: When sub_command is missing
        """
        if not args.sub_command:
            raise ArgumentError(args, "Missing sub-command")

        if args.sub_command not in self.sub_command_obj_dict:
            raise ArgumentError(
                    args,
                    "sub-command %s is not associated with any object" %
                    args.sub_command)
        obj = self.sub_command_obj_dict[args.sub_command]
        if inspect.isclass(obj):
            cls = obj
            if not hasattr(cls, 'init_from_parsed_args'):
                raise NoSuchMethodError('init_from_parsed_args')
            # New an object accordingto args
            obj = getattr(cls, 'init_from_parsed_args')(args)

        sub_cmd_obj = getattr(obj, args.sub_command)
        argspec = inspect.getargspec(sub_cmd_obj)
        arg_values = []
        for a in argspec.args:
            if a == 'self' or a == 'cls':
                continue
            arg_values.append(getattr(args, a))
        return sub_cmd_obj(*arg_values)


if __name__ == '__main__':
    if os.getenv("PY_DOCTEST", "0") == "1":
        import doctest
        test_result = doctest.testmod()
        print(doctest.testmod(), file=sys.stderr)
        sys.exit(0 if test_result.failed == 0 else 1)
    print("Legend of log levels", file=sys.stderr)
    ZanataArgParser('parser').parse_args(["-v", "DEBUG"])
    logging.debug("debug")
    logging.info("info")
    logging.warning("warning")
    logging.error("error")
    logging.critical("critical")
