#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The goal of `flexible configuration` is to make each script useful in a
variety of contexts and environments.

Attributes:
  LOGGER_NAME (str): logging.getLogger name

  SCRIPTHARNESS_INITIAL_CONFIG (dict): These key/value pairs are available
    in all scriptharness scripts.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
from copy import deepcopy
import json
import logging
import os
import requests
from requests.exceptions import RequestException, Timeout
from scriptharness.actions import Action
from scriptharness.exceptions import ScriptHarnessException, \
    ScriptHarnessTimeout, to_unicode
from scriptharness.structures import iterate_pairs
import six
import six.moves.urllib as urllib
import sys
import time


LOGGER_NAME = "scriptharness.config"
SCRIPTHARNESS_INITIAL_CONFIG = {
    "scriptharness_base_dir": six.text_type(os.getcwd()),
    "scriptharness_work_dir":
        "%(scriptharness_base_dir)s{}build".format(os.sep),
    "scriptharness_artifact_dir":
        "%(scriptharness_base_dir)s{}artifacts".format(os.sep),
}


# parse_config_file() {{{1
def parse_config_file(path):
    """Read a config file and return a dictionary.
    For now, only support json.

    Args:
      path (str): path or url to config file.

    Returns:
      config (dict): the parsed json dict.

    Raises:
      scriptharness.exceptions.ScriptHarnessException: if the path is
        unreadable or not valid json.
    """
    if is_url(path):
        path = download_url(path)
    # py3 may throw FileNotFoundError or IOError; both inherit OSError.
    # py2 throws IOError, which doesn't inherit OSError.
    if six.PY3:
        exception = OSError
    else:
        exception = IOError
    try:
        with open(path) as filehandle:
            config = dict(json.load(filehandle))
    except exception as exc_info:
        raise ScriptHarnessException(
            "Can't open path %s!" % path, exc_info
        )
    except ValueError as exc_info:
        raise ScriptHarnessException(
            "Can't parse json in %s!" % path, exc_info
        )
    return config


def get_filename_from_url(url):
    """Determine the filename of a file from its url.

    Args:
      url (str): the url to parse

    Returns:
      name (str): the name of the file
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.path != '':
        return parsed.path.rstrip('/').rsplit('/', 1)[-1]
    else:
        return parsed.netloc


def is_url(resource):
    """Is it a url?

    .. note:: This function will return False for `file://` strings

    Args:
      resource (str): possible url

    Returns:
      bool: True if it's a url, False otherwise.
    """
    parsed = urllib.parse.urlparse(resource)
    if parsed.scheme and parsed.netloc:
        return True
    return False


def download_url(url, path=None, timeout=None):
    """Download a url to a path.

    Args:
      url (str): the url to download
      path (str, optional): the path to write the contents to.
      timeout (float, optional): how long to wait before timing out.

    Returns:
      path (str): the path to the downloaded file.

    Raises:
      scriptharness.exceptions.ScriptHarnessException: if there are download
        issues, or if we can't write to path.
    """
    if path is None:
        path = get_filename_from_url(url)
    if timeout is None:
        timeout = 10
    try:
        with open(path, 'wb') as filehandle:
            try:
                start_time = time.time()
                session = requests.Session()
                session.mount(url, requests.adapters.HTTPAdapter(max_retries=5))
                response = session.get(url, timeout=timeout, stream=True)
                with open(path, 'wb') as filehandle:
                    for chunk in response.iter_content(  # pragma: no branch
                            chunk_size=1024):
                        if chunk:  # pragma: no branch
                            filehandle.write(chunk)
                            filehandle.flush()
                return path
            except RequestException as exc_info:
                if isinstance(exc_info, Timeout) or \
                        time.time() >= start_time + timeout:
                    raise ScriptHarnessTimeout(
                        "Timeout downloading from url %s" % url, exc_info
                    )
                raise ScriptHarnessException(
                    "Error downloading from url %s" % url, exc_info
                )
    except IOError as exc_info:
        raise ScriptHarnessException(
            "Error writing downloaded contents to path %s" % path, exc_info
        )


# get_parser() {{{1
def get_list_actions_string(action_name, enabled):
    """Build a string for --list-actions output.

    Args:
      action_name (str):  name of the action
      enabled (bool): whether the action is enabled by default

    Returns:
      string (str): a line of --list-actions output.
    """
    string = "  "
    if enabled:
        string = "* "
    string += action_name
    return string

def get_action_parser(all_actions):
    """Create an action option parser from the action list.

    Actions to run are specified as the argparse.REMAINDER options.

    Args:
      all_actions (iterable): this is either all Action objects for the
        script, or a data structure of pairs of action_name:enabled to pass
        to iterate_pairs().

      **kwargs: additional kwargs for ArgumentParser

    Returns:
      ArgumentParser with action options
    """
    parser = argparse.ArgumentParser(add_help=False)
    message = []
    choices = []
    for action in all_actions:
        if isinstance(action, Action):
            choices.append(action.name)
            message.append(
                get_list_actions_string(action.name, action.enabled)
            )
        else:
            message = []
            choices = []
            for name, enabled in iterate_pairs(all_actions):
                message.append(get_list_actions_string(name, enabled))
                choices.append(name)
            break
    def list_actions():
        """Helper function to list all actions (enabled shown with a '*')"""
        print(os.linesep.join(message))
        sys.exit(0)
    parser.add_argument(
        "--list-actions", action='store_const', const=list_actions,
        dest="scriptharness_volatile_list_actions",
        help="List all actions (default prepended with '*') and exit."
    )
    parser.add_argument(
        "--actions", nargs='+', choices=choices, metavar="ACTION",
        dest="scriptharness_volatile_actions",
        help="Specify the actions to run."
    )
    return parser

def get_config_parser():
    """Create a config option parser.

    Args:
      kwargs: additional kwargs for ArgumentParser

    Returns:
      ArgumentParser with config options
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--config-file', '--cfg', '-c', action='append', dest='config_files',
        metavar="CONFIG_FILE", help="Specify required config files/urls"
    )
    parser.add_argument(
        '--opt-config-file', '--opt-cfg', action='append',
        dest='opt_config_files', metavar="CONFIG_FILE",
        help="Specify optional config files/urls"
    )
    parser.add_argument(
        '--dump-config', action='store_true',
        dest="scriptharness_volatile_dump_config",
        help="Log the built configuration and exit."
    )
    return parser


def get_parser(all_actions=None, parents=None, **kwargs):
    """Create a script option parser.

    Args:
      parents (list, optional): ArgumentParsers to set as parents of the parser
      **kwargs: additional kwargs for ArgumentParser

    Returns:
      ArgumentParser with config options
    """
    if parents is None:
        parents = []
        if all_actions:
            parents.append(get_action_parser(all_actions))
        parents.append(get_config_parser())
    parser = argparse.ArgumentParser(parents=parents, **kwargs)
    return parser


def parse_args(parser, cmdln_args=None):
    """Build the parser and parse the commandline args.

    Args:
      parser (ArgumentParser): specify the parser to use
      cmdln_args (optional): override the commandline args with these

    Returns:
      tuple(ArgumentParser, parsed_args)
    """
    args = []
    if cmdln_args is not None:  # pragma: no branch
        args.append(cmdln_args)
    parsed_args = parser.parse_args(*args)
    if hasattr(parsed_args, 'scriptharness_volatile_list_actions') and \
            callable(parsed_args.scriptharness_volatile_list_actions):
        parsed_args.scriptharness_volatile_list_actions()
    return parsed_args


# build_config {{{1

def update_dirs(config, max_depth=2):
    """Directory paths for the script are defined in config.
    Absolute paths help avoid chdir issues.

    `scriptharness_base_dir` (or any other directory path, or any config value)
    can be overridden during build_config().  Defining the directory paths as
    formattable strings is configurable but not overly complex.

    Any key in `config` named scriptharness_SOMETHING_dir will be % formatted
    with the other dirs as the replacement dictionary.

    Args:
      config (dict): the config to parse for scriptharness_SOMETHING_dir keys.
    """
    repl_dict = {}
    for key, value in config.items():
        if key.startswith("scriptharness_") and key.endswith("_dir"):
            repl_dict[key] = value
    # Make a couple expansion passes, in case a dir is based on another dir
    # with a % formatting string.
    for _ in range(max_depth):
        for key in repl_dict:
            repl_dict[key] = repl_dict[key] % repl_dict
    config.update(repl_dict)

def build_config(parser, parsed_args, initial_config=None):
    """Build a configuration dict from the parser and initial config.

    The configuration is built in this order:

      * parser defaults
      * initial_config
      * parsed_args.config_files, in order
      * parsed_args.opt_config_files, in order, if they exist
      * non-default parser args (cmdln_args)

    So the commandline args can override everything else, as long as there are
    options to do so. (Commandline args will need to be a subset of the parser
    args).  The final configuration file can override everything but the
    commandline args, and its config isn't restricted as a subset of the
    parser options.

    Args:
      parser (ArgumentParser): the parser used to parse_args()
      parsed_args (argparse Namespace): the results of parse_args()
      initial_config (dict, optional): initial configuration to set before
        commandline args
    """
    config = deepcopy(SCRIPTHARNESS_INITIAL_CONFIG)
    cmdln_config = {}
    resources = {}
    initial_config = initial_config or {}
    logger = logging.getLogger(LOGGER_NAME)
    for key, value in parsed_args.__dict__.items():
        if key.startswith('scriptharness_') and '_volatile_' in key:
            continue
        if key in ('config_files', 'opt_config_files'):
            resources.setdefault(key, value or [])
            continue
        if parser.get_default(key) == value:
            config[to_unicode(key)] = to_unicode(value)
        else:
            cmdln_config[key] = value
    config.update(initial_config)
    for resource in resources.get('config_files', []):
        config.update(parse_config_file(resource))
    for resource in resources.get('opt_config_files', []):
        try:
            config.update(parse_config_file(resource))
        except ScriptHarnessException:
            logger.info("Can't read optional config file %s; skipping.",
                        resource)
    if cmdln_config:
        config.update(cmdln_config)
    update_dirs(config)
    return config
