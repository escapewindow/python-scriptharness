#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Wrapping python os and related functions.

Args:
  LOGGER_NAME (str): the default logging.Logger name
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import logging
import os

LOGGER_NAME = "scriptharness.files"


def makedirs(path, level=logging.INFO, context=None):
    """os.makedirs() wrapper.

    Args:
      path (str): path to the directory
      level (int, optional): the logging level to log with.
    """
    if context:
        logger = context.logger
    else:
        logger = logging.getLogger(LOGGER_NAME)
    logger.log(level, "Creating directory %s", path)
    if not os.path.exists(path):
        os.makedirs(path)
        logger.log(level, "Done.")
    else:
        logger.log(level, "Already exists.")

def make_parent_dir(path, **kwargs):
    """Create the parent of path if it doesn't exist.

    Args:
      path (str): path to the file.
      **kwargs: These are passed to makedirs().
    """
    dirname = os.path.dirname(path)
    if dirname:
        makedirs(dirname, **kwargs)
