#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/os.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import os
import scriptharness.files as sh_files
import shutil
import unittest
from . import LoggerReplacement

TEST_DIR = "this_dir_should_not_exist"


class TestContext(object):
    """Context for test logging
    """
    logger = None
    def __init__(self):
        self.new_logger()
    def new_logger(self):
        """Create a new logger"""
        self.logger = LoggerReplacement()
    def silence_pylint(self):
        """silence pylint"""
        assert self

def cleanup():
    """Cleanliness"""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

class TestFunctions(unittest.TestCase):
    """Test the os functions
    """
    def setUp(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    def tearDown(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    def test_makedirs(self):
        """test_os | make_parent_dir()
        """
        context = TestContext()
        self.assertFalse(os.path.exists(TEST_DIR))
        sh_files.make_parent_dir(os.path.join(TEST_DIR, "foo", "bar"),
                                 context=context)
        self.assertTrue(os.path.isdir(os.path.join(TEST_DIR, "foo")))
        messages = context.logger.all_messages[:]
        # This should be noop; verifying by no change in all_messages
        sh_files.make_parent_dir(TEST_DIR, context=context)
        self.assertEqual(messages, context.logger.all_messages)
        # This should also be noop.  Boo hardcoded string.
        sh_files.makedirs(TEST_DIR, context=context)
        self.assertEqual(context.logger.all_messages[-1][1], "Already exists.")
