#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Error tuples are used to parse output in scriptharness.log.OutputParser.

Each line of output is matched against each substring or regular expression
in the error tuple.  On a match, we determine the 'level' of that line.
Levels are ints, and match the levels in the python logging module.  Negative
levels are ignored.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import logging
import re
from scriptharness.exceptions import ScriptHarnessException, \
    ScriptHarnessFatal
import six


# ErrorTuple helper methods {{{1
def exactly_one(key1, key2, error_check, messages):
    """Make sure one, and only one, of key1 and key2 are in error_check.
    If that's not the case, append an error message in messages.

    Args:
      key1 (str): Dictionary key.

      key2 (str): Dictionary key.

      error_check (dict): a single item of error_tuple.

      messages (list): the list of error messages so far.

    Returns:
      Bool: True if there is exactly one of the two keys in error_check.
    """
    status = True
    error_check_str = six.text_type(error_check)
    if key1 not in error_check and key2 not in error_check:
        messages.append(
            "%s must contain '%s' or '%s'!" % (error_check_str, key1, key2)
        )
        status = False
    elif key1 in error_check and key2 in error_check:
        messages.append(
            "%s has both '%s' and '%s'!" % (error_check_str, key1, key2)
        )
        status = False
    return status

def verify_unicode(key, error_check, messages):
    """If key is in error_check, it must be of type six.text_type.
    If not, append an error message to messages.

    Args:
      key (str): a dict key
      error_check (dict): a single item of error_tuple
      messages (list): The error messages so far
    """
    if key in error_check and not \
            isinstance(error_check[key], six.text_type):
        messages.append(
            "%s %s is not of type %s!" % (error_check, key, six.text_type)
        )

def check_ignore(strict, ignore, message, messages):
    """If the level of an error_check is negative, it will be ignored.
    There is currently no pre_context_lines or post_context_lines support
    for ignored lines.  When self.strict is True, append an error to
    messages.

    Args:
      ignore (bool): True when 'level' is in error_check and negative.
      name (str): The name of the key (pre_context_lines,
        post_context_lines)
      error_check (dict): A single item of error_tuple
      messages (list): The error messages so far.
    """
    if ignore and strict:
        messages.append(message)

def check_context_lines(context_lines, orig_context_lines, name, messages):
    """Verifies and returns the larger int of context_lines and
    orig_context_lines.

    Args:
      context_lines (value): The value of pre_context_lines or
        post_context_lines to validate.

      orig_context_lines (int): The previous max int sent to
        check_context_lines

      name (str): The name of the field (pre_context_lines or
        post_context_lines)

      messages (list): The list of error messages so far.

    Returns:
      int: If context_lines is a non-int or negative, an error is appended
        to messages and we return orig_context_lines.  Otherwise, we return
        the max of context_lines or orig_context_lines.
    """
    if not isinstance(context_lines, int) or context_lines < 0:
        messages.append(
            "%s %s must be a positive int!" %
            (name, six.text_type(context_lines))
        )
        return orig_context_lines
    return max(context_lines, orig_context_lines)


# ErrorTuple {{{1
class ErrorTuple(tuple):
    """Error tuples, to describe how to parse output.  In object form for
    better validation.

    An example error_tuple::

        [
            {
                "regex": re.compile("^Error: not actually an error!"),
                level=-1
            }, {
                "regex": re.compile("^Error:"),
                "level": logging.ERROR,
                "pre_context_lines": 5,
                "post_context_lines": 5
            }, {
                "substr": "Obscure error #94382",
                "explanation":
                    "This is a fatal program error."
                "exception": ScriptHarnessFatal
            }
        ]

    Any output line that matches the first regex will be ignored (discarded),
    because level is negative.  Because the list is matched in order, the
    more specific regex is placed before the more general 2nd regex.  If the
    order were reversed, the more specific regex would never match anything.
    The second regex sets the level to logging.ERROR for this line, and 5
    lines above and 5 lines below this message.

    Attributes:
      strict (bool): If True, be more strict about well-formed error_tuples.
      pre_context_lines (int): The max number of lines the error_tuple defines
        in pre_context_lines.
      post_context_lines (int): The max number of lines the error_tuple defines
        in post_context_lines.
      error_tuple (tuple of dicts): The error tuple.
    """
    def __init__(self, error_tuple, strict=True):
        tuple.__init__(error_tuple)
        self.strict = strict
        (self.pre_context_lines, self.post_context_lines) = \
            self.validate_error_tuple(error_tuple)

    def validate_error_tuple(self, error_tuple):
        """Validate an error_tuple.
        This is going to be a pain to unit test properly.

        Args:
          error_tuple (tuple of dicts): an error_tuple.

        Returns:
          (pre_context_lines, post_context_lines) (tuple of int, int)

        Raises:
          scriptharness.exceptions.ScriptHarnessException: if error_tuple is not
            well-formed.
        """
        messages = []
        context_lines_re = re.compile(r'^(\d+):(\d+)')
        re_compile_class = context_lines_re.__class__
        pre_context_lines = 0
        post_context_lines = 0
        for error_check in error_tuple:
            ignore = False
            error_check_str = six.text_type(error_check)
            if not isinstance(error_check, dict):
                messages.append("%s is not a dict!" % error_check_str)
                continue
            if 'level' in error_check:
                if not isinstance(error_check['level'], int):
                    messages.append(
                        "%s level must be an int!" % error_check_str
                    )
                elif error_check['level'] < 0:
                    ignore = True
            elif 'exception' not in error_check:
                messages.append(
                    "%s level must be set if exception is not set!" %
                    error_check_str
                )
            if 'exception' in error_check and (not \
                    isinstance(error_check['exception'], type) or not \
                    issubclass(error_check['exception'], Exception)):
                messages.append(
                    "%s exception must be a subclass of Exception!" %
                    error_check_str
                )
            exactly_one('substr', 'regex', error_check, messages)
            verify_unicode('substr', error_check, messages)
            if 'regex' in error_check and not \
                    isinstance(error_check['regex'], re_compile_class):
                messages.append(
                    "%s regex needs to be re.compile'd!" % error_check_str
                )
            if 'pre_context_lines' in error_check:
                pre_context_lines = check_context_lines(
                    error_check['pre_context_lines'], pre_context_lines,
                    "pre_context_lines", messages
                )
                check_ignore(
                    self.strict, ignore,
                    "%s 'pre_context_lines' will be ignored because 'level'"
                    " < 0." % error_check, messages
                )
            if 'post_context_lines' in error_check:
                post_context_lines = check_context_lines(
                    error_check['post_context_lines'], post_context_lines,
                    "post_context_lines", messages
                )
                check_ignore(
                    self.strict, ignore,
                    "%s 'post_context_lines' will be ignored because 'level'"
                    " < 0." % error_check, messages
                )
            verify_unicode('explanation', error_check, messages)
        if messages:
            raise ScriptHarnessException(messages)
        return (pre_context_lines, post_context_lines)


# ErrorTuples {{{1
# These are largely taken from mozharness.
BASE_ERROR_TUPLE = ErrorTuple([{
    'substr': 'command not found', 'level': logging.ERROR
}])

# For ssh, scp, rsync over ssh
SSH_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [
    {'substr': 'Name or service not known', 'level': logging.ERROR},
    {'substr': 'Could not resolve hostname', 'level': logging.ERROR},
    {'substr': 'POSSIBLE BREAK-IN ATTEMPT', 'level': logging.WARNING},
    {'substr': 'Network error:', 'level': logging.ERROR},
    {'substr': 'Access denied', 'level': logging.ERROR},
    {'substr': 'Authentication refused', 'level': logging.ERROR},
    {'substr': 'Out of memory', 'level': logging.ERROR},
    {'substr': 'Connection reset by peer', 'level': logging.WARNING},
    {'substr': 'Host key verification failed', 'level': logging.ERROR},
    {'substr': 'logging.WARNING:', 'level': logging.WARNING},
    {'substr': 'rsync error:', 'level': logging.ERROR},
    {'substr': 'Broken pipe:', 'level': logging.ERROR},
    {'substr': 'Permission denied:', 'level': logging.ERROR},
    {'substr': 'connection unexpectedly closed', 'level': logging.ERROR},
    {'substr': 'Warning: Identity file', 'level': logging.ERROR},
    {'substr': 'command-line line 0: Missing argument',
     'level': logging.ERROR},
])

HG_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [{
    'regex': re.compile(r'^abort:'),
    'level': logging.ERROR,
    'explanation': 'Automation Error: hg not responding'
}, {
    'substr': 'unknown exception encountered',
    'level': logging.ERROR,
    'explanation': 'Automation Error: python exception in hg'
}, {
    'substr': 'failed to import extension',
    'level': logging.WARNING,
    'explanation': 'Automation Error: hg extension missing'
}])

GIT_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [
    {'substr': 'Permission denied (publickey).', 'level': logging.ERROR},
    {'substr': 'fatal: The remote end hung up unexpectedly',
     'level': logging.ERROR},
    {'substr': 'does not appear to be a git repository',
     'level': logging.ERROR},
    {'substr': 'error: src refspec', 'level': logging.ERROR},
    {'substr': 'invalid author/committer line -', 'level': logging.ERROR},
    {'substr': 'remote: fatal: Error in object', 'level': logging.ERROR},
    {'substr': "fatal: sha1 file '<stdout>' write error: Broken pipe",
     'level': logging.ERROR},
    {'substr': 'error: failed to push some refs to ', 'level': logging.ERROR},
    {'substr': 'remote: error: denying non-fast-forward ',
     'level': logging.ERROR},
    {'substr': '! [remote rejected] ', 'level': logging.ERROR},
    {'regex': re.compile(r'remote:.*No such file or directory'),
     'level': logging.ERROR},
])

PYTHON_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [
    {'regex': re.compile(r'Warning:.*Error: '), 'level': logging.WARNING},
    {'substr': 'Traceback (most recent call last)', 'level': logging.ERROR},
    {'substr': 'SyntaxError: ', 'level': logging.ERROR},
    {'substr': 'TypeError: ', 'level': logging.ERROR},
    {'substr': 'NameError: ', 'level': logging.ERROR},
    {'substr': 'ZeroDivisionError: ', 'level': logging.ERROR},
    {'regex': re.compile(r'raise \w*Exception: '), 'level': logging.CRITICAL},
    {'regex': re.compile(r'raise \w*Error: '), 'level': logging.CRITICAL},
])

VIRTUALENV_ERROR_TUPLE = ErrorTuple([
    {'substr': 'not found or a compiler error:', 'level': logging.WARNING},
    {'regex': re.compile(r'\d+: error: '), 'level': logging.ERROR},
    {'regex': re.compile(r'\d+: warning: '), 'level': logging.WARNING},
    {
        'regex': re.compile(
            r'Downloading .* \(.*\): *([0-9]+%)? *[0-9\.]+[kmKM]b'
        ),
        'level': logging.DEBUG
    },
] + list(PYTHON_ERROR_TUPLE))

MAKE_ERROR_TUPLE = ErrorTuple(list(PYTHON_ERROR_TUPLE) + [
    {'substr': 'No rule to make target ', 'level': logging.ERROR},
    {'regex': re.compile(r'akefile.*was not found\.'), 'level': logging.ERROR},
    {'regex': re.compile(r'Stop\.$'), 'level': logging.ERROR},
    {'regex': re.compile(r':\d+: error:'), 'level': logging.ERROR},
    {'regex': re.compile(r'make\[\d+\]: \*\*\* \[.*\] Error \d+'),
     'level': logging.ERROR},
    {'regex': re.compile(r':\d+: warning:'), 'level': logging.WARNING},
    {'regex': re.compile(r'make(?:\[\d+\])?: \*\*\*/'),
     'level': logging.ERROR},
    {'substr': 'Warning: ', 'level': logging.WARNING},
])

TAR_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [
    {'substr': '(stdin) is not a bzip2 file.', 'level': logging.ERROR},
    {'regex': re.compile(r'Child returned status [1-9]'),
     'level': logging.ERROR},
    {'substr': 'Error exit delayed from previous errors',
     'level': logging.ERROR},
    {'substr': 'stdin: unexpected end of file', 'level': logging.ERROR},
    {'substr': 'stdin: not in gzip format', 'level': logging.ERROR},
    {'substr': 'Cannot exec: No such file or directory',
     'level': logging.ERROR},
    {'substr': ': Error is not recoverable: exiting now',
     'level': logging.ERROR},
])

ADB_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [
    {'substr': 'INSTALL_FAILED_', 'level': logging.ERROR},
    {'substr': 'Android Debug Bridge version', 'level': logging.ERROR},
    {'substr': 'error: protocol fault', 'level': logging.ERROR},
    {'substr': 'unable to connect to ', 'level': logging.ERROR},
])

JARSIGNER_ERROR_TUPLE = ErrorTuple([{
    'substr': 'command not found',
    'level': logging.CRITICAL, 'exception': ScriptHarnessFatal,
}, {
    'substr': 'jarsigner error: java.lang.RuntimeException: keystore load: '
              'Keystore was tampered with, or password was incorrect',
    'level': logging.CRITICAL, 'exception': ScriptHarnessFatal,
    'explanation': 'The store passphrase is probably incorrect!',
}, {
    'regex': re.compile(
        r'jarsigner: key associated with .* not a private key'
    ),
    'level': logging.CRITICAL, 'exception': ScriptHarnessFatal,
    'explanation': 'The key passphrase is probably incorrect!',
}, {
    'regex': re.compile(
        r'jarsigner error: java.lang.RuntimeException: keystore load: .* '
        r'.No such file or directory'
    ),
    'level': logging.CRITICAL, 'exception': ScriptHarnessFatal,
    'explanation': "The keystore doesn't exist!",
}, {
    'substr': 'jarsigner: unable to open jar file:',
    'level': logging.CRITICAL, 'exception': ScriptHarnessFatal,
    'explanation': 'The apk is missing!',
}])

ZIP_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [{
    'substr': 'zip warning:',
    'level': logging.WARNING,
}, {
    'substr': 'zip error:',
    'level': logging.ERROR,
}, {
    'substr': 'Cannot open file: it does not appear to be a valid archive',
    'level': logging.ERROR,
}])

ZIPALIGN_ERROR_TUPLE = ErrorTuple(list(BASE_ERROR_TUPLE) + [{
    'regex': re.compile(r'Unable to open .* as a zip archive'),
    'level': logging.ERROR,
}, {
    'regex': re.compile(r'Output file .* exists'),
    'level': logging.ERROR,
}, {
    'substr': "Input and output can't be the same file",
    'level': logging.ERROR,
}])
