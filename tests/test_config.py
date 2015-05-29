#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/config.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
import mock
import os
import requests
from scriptharness.actions import Action
import scriptharness.config as shconfig
from scriptharness.exceptions import ScriptHarnessException
import six
import subprocess
import sys
import time
import unittest

from . import TEST_ACTIONS, stdstar_redirected

if six.PY3:
    BUILTIN = 'builtins'
else:
    BUILTIN = '__builtin__'

TEST_FILE = '_test_config_file'
TEST_FILES = (TEST_FILE, 'invalid_json.json', 'test_config.json')


# Helper functions {{{1
def cleanup():
    """Cleanup helper function"""
    for path in TEST_FILES:
        if os.path.exists(path):
            os.remove(path)

@contextmanager
def start_webserver():
    """Start a webserver for local requests testing
    """
    port = 8001
    max_wait = 5
    wait = 0
    interval = .02
    host = "http://localhost:%s" % str(port)
    dir_path = os.path.join(os.path.dirname(__file__), 'http')
    file_path = os.path.join(dir_path, 'cgi_server.py')
    proc = subprocess.Popen([sys.executable, file_path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while wait < max_wait:
        try:
            response = requests.get(host)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(interval)
        wait += interval
    try:
        yield (dir_path, host)
    finally:
        proc.terminate()
        # make sure it goes away
        try:
            while True:
                response = requests.get(host)
        except requests.exceptions.ConnectionError:
            pass

# TestUrlFunctions {{{1
class TestUrlFunctionss(unittest.TestCase):
    """Test url functions
    """
    def setUp(self):
        assert self  # silence pylint
        cleanup()

    def tearDown(self):
        assert self  # silence pylint
        cleanup()

    def test_basic_url_filename(self):
        """test_config | Filename from a basic url"""
        url = "http://example.com/bar/baz"
        self.assertEqual(shconfig.get_filename_from_url(url), "baz")

    def test_no_path(self):
        """test_config | Filename from a url without a path"""
        url = "https://example.com"
        self.assertEqual(shconfig.get_filename_from_url(url), "example.com")

    def test_is_url(self):
        """test_config | Verify is_url(real_url)"""
        for url in ("http://example.com", "https://example.com/foo/bar"):
            self.assertTrue(shconfig.is_url(url))

    def test_is_not_url(self):
        """test_config | Verify not is_url(real_url)"""
        for url in ("example.com", "/usr/local/bin/python",
                    "c:\\temp\\"):
            print(url)
            self.assertFalse(shconfig.is_url(url))

    @unittest.skipIf(os.name == 'nt' and six.PY3,
                     "OSError: [WinError 6] The handle is invalid "
                     "http://bugs.python.org/issue3905 ?")
    def test_successful_download_url(self):
        """test_config | Download a file from a local webserver.
        """
        with start_webserver() as (path, host):
            with open(os.path.join(path, "test_config.json")) as filehandle:
                orig_contents = filehandle.read()
            shconfig.download_url("%s/test_config.json" % host, path=TEST_FILE)
        with open(TEST_FILE) as filehandle:
            contents = filehandle.read()
        self.assertEqual(contents, orig_contents)

    def test_empty_download_url(self):
        """test_config | Download an empty file from a local webserver.
        """
        with start_webserver() as (_, host):
            shconfig.download_url("%s/empty_file" % host, path=TEST_FILE)
        with open(TEST_FILE) as filehandle:
            contents = filehandle.read()
        self.assertEqual(contents, "")

    @unittest.skipIf(os.name == 'nt',
                     "windows downloads the cgi instead of running")
    def test_timeout_download_url(self):
        """test_config | Time out in download_url()
        """
        with start_webserver() as (_, host):
            self.assertRaises(
                ScriptHarnessException,
                shconfig.download_url, "%s/cgi-bin/timeout.cgi" % host,
                timeout=.1
            )

    def test_ioerror_download_url(self):
        """test_config | Download with unwritable target file.
        """
        with start_webserver() as (path, host):
            self.assertRaises(
                ScriptHarnessException,
                shconfig.download_url,
                "%s/test_config.json" % host, path=path
            )

    def test_parse_config_file(self):
        """test_config | parse json
        """
        path = os.path.join(os.path.dirname(__file__), 'http',
                            'test_config.json')
        config = shconfig.parse_config_file(path)
        with open(path) as filehandle:
            config2 = json.load(filehandle)
        self.assertEqual(config, config2)

    def test_parse_invalid_json(self):
        """test_config | Download invalid json and parse it
        """
        with start_webserver() as (_, host):
            self.assertRaises(
                ScriptHarnessException,
                shconfig.parse_config_file,
                "%s/invalid_json.json" % host
            )

    def test_parse_invalid_path(self):
        """test_config | Parse nonexistent file
        """
        self.assertRaises(
            ScriptHarnessException,
            shconfig.parse_config_file,
            "%s/nonexistent_file" % __file__
        )


# TestParserFunctions {{{1
class TestParserFunctions(unittest.TestCase):
    """Test parser functions
    """
    @staticmethod
    @mock.patch('%s.print' % BUILTIN)
    def test_list_actions(mock_print):
        """test_config | --list-actions
        """
        parser = shconfig.get_parser(all_actions=TEST_ACTIONS)
        try:
            shconfig.parse_args(parser, cmdln_args=["--list-actions"])
        except SystemExit:
            pass
        mock_print.assert_called_once_with(
            os.linesep.join(
                ["  clobber", "* pull", "* build", "* package", "  upload",
                 "  notify"]
            )
        )

    def test_action_parser(self):
        """test_config | action parser
        """
        actions = []
        def func():
            """test function"""
            pass
        for name, enabled in TEST_ACTIONS:
            actions.append(Action(name, enabled=enabled, function=func))
        parser = shconfig.get_action_parser(actions)
        args = parser.parse_args("--actions build package".split())
        self.assertEqual(args.scriptharness_volatile_actions,
                         ["build", "package"])
        with stdstar_redirected(os.devnull):
            self.assertRaises(SystemExit, parser.parse_args,
                              "--actions invalid_action".split())

    def test_config_parser(self):
        """test_config | config parser
        """
        parser = shconfig.get_config_parser()
        args = parser.parse_args("-c file1 -c file2 -c file3".split())
        self.assertEqual(
            args.config_files,
            ["file1", "file2", "file3"]
        )

    def test_no_actions(self):
        """test_config | no actions, get_parser no kwargs
        """
        parser = shconfig.get_parser()
        with stdstar_redirected(os.devnull):
            self.assertRaises(SystemExit, parser.parse_args, ["--list-actions"])

    def test_no_actions2(self):
        """test_config | no actions, setting get_parser parents
        """
        parents = []
        parser = shconfig.get_parser(parents=parents)
        parsed_args = shconfig.parse_args(parser, cmdln_args=[])
        self.assertEqual(parsed_args, argparse.Namespace())

    def helper_build_config(self, cmdln_args, initial_config=None):
        """Help test build_config()
        """
        config2 = deepcopy(shconfig.SCRIPTHARNESS_INITIAL_CONFIG)
        shconfig.update_dirs(config2)
        if initial_config is None:
            initial_config = {
                "key1": "value0",
                "key2": "value0",
                "additional_config_item": 234,
            }
        config2.update(initial_config)
        path = os.path.join(os.path.dirname(__file__), 'http',
                            'test_config.json')
        with open(path) as filehandle:
            contents = json.load(filehandle)
        parser = shconfig.get_parser(all_actions=TEST_ACTIONS)
        parser.add_argument("--test-default", default="default")
        parser.add_argument("--override-default", default="default")
        parsed_args = shconfig.parse_args(parser, cmdln_args=cmdln_args)
        config = shconfig.build_config(parser, parsed_args, initial_config)
        config2.update(contents)
        config2['test_default'] = 'default'
        config2['override_default'] = 'not_default'
        self.assertEqual(config, config2)

    def test_build_config_optcfg(self):
        """test_config | build_config() optcfg
        """
        path = os.path.join(os.path.dirname(__file__), 'http',
                            'test_config.json')
        cmdln_args = ["-c", path, "--actions", "build", "package",
                      "--override-default", "not_default",
                      "--opt-cfg", "%s/nonexistent_file" % __file__]
        self.helper_build_config(cmdln_args)

    def test_build_config_nocfg(self):
        """test_config | build_config() no cfg files
        """
        cmdln_args = ["--actions", "build", "package",
                      "--override-default", "not_default"]
        path = os.path.join(os.path.dirname(__file__), 'http',
                            'test_config.json')
        with open(path) as filehandle:
            contents = json.load(filehandle)
        initial_config = {
            "additional_config_item": 234,
        }
        initial_config.update(contents)
        self.helper_build_config(cmdln_args, initial_config=initial_config)

    def test_build_config_nocmdln(self):
        """test_config | build_config() no cmdln
        """
        cmdln_args = []
        path = os.path.join(os.path.dirname(__file__), 'http',
                            'test_config.json')
        with open(path) as filehandle:
            contents = json.load(filehandle)
        initial_config = {
            "additional_config_item": 234,
            "override_default": "not_default",
        }
        initial_config.update(contents)
        self.helper_build_config(cmdln_args, initial_config=initial_config)
