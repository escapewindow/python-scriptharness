#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scriptharness exceptions.

These exceptions are written with several things in mind:

 #. the exceptions should be unicode-capable in python 2.7 (py3 gets that
    for free),
 #. the exceptions should differentiate between user-facing exceptions and
    developer-facing exceptions, and
 #. ScriptHarnessFatal should exit the script.

There may be more exceptions in the future, to further differentiate between
errors.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from scriptharness.unicode import to_unicode
import six


@six.python_2_unicode_compatible
class ScriptHarnessBaseException(Exception):
    """All scriptharness exceptions should inherit this exception.

    However, in most cases you probably want to catch ScriptHarnessException
    instead.
    """
    def __str__(self):
        """This method will become __unicode__() in py2 via the
        @six.python_2_unicode_compatible decorator.
        """
        if six.PY3:
            string = super(ScriptHarnessBaseException, self).__str__()
        else:
            string = super(ScriptHarnessBaseException, self).message
        string = to_unicode(string, 'utf-8')
        return string


class ScriptHarnessException(ScriptHarnessBaseException):
    """There is a problem in how scriptharness is being called.
    All developer-facing exceptions should inherit this class.

    If you want to catch all developer-facing scriptharness exceptions,
    catch ScriptHarnessException.
    """


class ScriptHarnessTimeout(ScriptHarnessException):
    """There was a timeout while running scriptharness.
    """


class ScriptHarnessError(ScriptHarnessBaseException):
    """User-facing exception.

    Scriptharness has detected an error in the running process.

    Since this exception is not designed to always exit, it's best to
    catch these and deal with the error.
    """


class ScriptHarnessFatal(SystemExit, ScriptHarnessBaseException):
    """User-facing exception.

    Scriptharness has detected a fatal failure in the running process.
    This exception should result in program termination; using try/except may
    result in unexpected or dangerous behavior.
    """
    def __str__(self):
        return ScriptHarnessBaseException.__str__(self)
