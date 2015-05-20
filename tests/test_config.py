#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/config.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from contextlib import contextmanager
import json
import mock
import os
import requests
from scriptharness import ScriptHarnessException
import scriptharness.config as shconfig
import six
import subprocess
import sys
import time
import unittest

from . import TEST_ACTIONS

if six.PY3:
    BUILTIN = 'builtins'
else:
    BUILTIN = '__builtin__'

TEST_FILE = '_test_config_file'
TEST_FILES = (TEST_FILE, 'invalid_json.json', 'test_config.json')


# Helper functions {{{1
def nuke_test_files():
    """Cleanup helper function"""
    for path in TEST_FILES:
        if os.path.exists(path):
            os.remove(path)

@contextmanager
def start_webserver():
    """Start a webserver for local requests testing
    """
    port = 8001  # TODO get free port
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
        nuke_test_files()

    def tearDown(self):
        assert self  # silence pylint
        nuke_test_files()

    def test_basic_url_filename(self):
        """Filename from a basic url"""
        url = "http://example.com/bar/baz"
        self.assertEqual(shconfig.get_filename_from_url(url), "baz")

    def test_no_path(self):
        """Filename from a url without a path"""
        url = "https://example.com"
        self.assertEqual(shconfig.get_filename_from_url(url), "example.com")

    def test_is_url(self):
        """Verify is_url(real_url)"""
        for url in ("http://example.com", "https://example.com/foo/bar",
                    "file:///home/example/.bashrc"):
            self.assertTrue(shconfig.is_url(url))

    def test_is_not_url(self):
        """Verify not is_url(real_url)"""
        for url in ("example.com", "/usr/local/bin/python"):
            print(url)
            self.assertFalse(shconfig.is_url(url))

    def test_successful_download_url(self):
        """Download a file from a local webserver.
        """
        with start_webserver() as (path, host):
            with open(os.path.join(path, "test_config.json")) as filehandle:
                orig_contents = filehandle.read()
            shconfig.download_url("%s/test_config.json" % host, path=TEST_FILE)
        with open(TEST_FILE) as filehandle:
            contents = filehandle.read()
        self.assertEqual(contents, orig_contents)

    def test_timeout_download_url(self):
        """Time out in download_url()
        """
        with start_webserver() as (_, host):
            self.assertRaises(
                ScriptHarnessException,
                shconfig.download_url, "%s/cgi-bin/timeout.cgi" % host,
                timeout=.1
            )

    def test_ioerror_download_url(self):
        """Download with unwritable target file.
        """
        with start_webserver() as (path, host):
            self.assertRaises(
                ScriptHarnessException,
                shconfig.download_url,
                "%s/test_config.json" % host, path=path
            )

    def test_parse_config_file(self):
        """parse json
        """
        path = os.path.join(os.path.dirname(__file__), 'http',
                            'test_config.json')
        config = shconfig.parse_config_file(path)
        with open(path) as filehandle:
            config2 = json.load(filehandle)
        self.assertEqual(config, config2)

    def test_parse_invalid_json(self):
        """Download invalid json and parse it
        """
        with start_webserver() as (_, host):
            self.assertRaises(
                ScriptHarnessException,
                shconfig.parse_config_file,
                "%s/invalid_json.json" % host
            )

    def test_parse_invalid_path(self):
        """Parse nonexistent file
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
        """Test --list-actions
        """
        parser = shconfig.get_action_parser(TEST_ACTIONS)
        args = parser.parse_args(["--list-actions"])
        try:
            args.list_actions()
        except SystemExit:
            pass
        mock_print.assert_called_once_with(
            os.linesep.join(
                ["  clobber", "* pull", "* build", "* package", "  upload",
                 "  notify"]
            )
        )
