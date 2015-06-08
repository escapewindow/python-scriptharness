#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness.log

Attributes:
  TEST_FILE (str): the filename to use for test log files
  TEST_CONSOLE (str): the filename to use for testing console output
  TEST_FILE_CONTENTS (str): a string to prepopulate logs to test overwriting
  TEST_STRING (str): a sample ascii string to use to test log output
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import codecs
from contextlib import contextmanager
import logging
import mock
import os
import pprint
import re
from scriptharness.errorlists import ErrorList
from scriptharness.exceptions import ScriptHarnessException, \
    ScriptHarnessError
import scriptharness.log as log
import unittest
from . import UNICODE_STRINGS, LOGGER_NAME, LoggerReplacement, \
              stdstar_redirected


TEST_FILE = '_test_log_file'
TEST_CONSOLE = '_test_log_console'
TEST_FILE_CONTENTS = "Newly initialized test file"
TEST_STRING = "This is a test string"

# Helper methods {{{1
def _absent_test_file(path=TEST_FILE):
    """Return a test file path that doesn't exist.
    """
    if os.path.exists(path):
        os.remove(path)
    assert not os.path.exists(path)
    return path

def _present_test_file(path=TEST_FILE, contents=None):
    """Return a test file path that exists with initialized content.
    """
    with open(path, 'w') as filehandle:
        if contents is not None:
            print(TEST_FILE_CONTENTS, file=filehandle)
    return path

class NoPostFunc(log.LogMethod):
    """Subclass LogMethod to only log from pre_func()
    """
    def call_func(self):
        """Skip calling"""
        pass
    def post_func(self):
        """Skip logging"""
        pass

def always_fail_cb(*args):
    """always fail"""
    return True

def always_succeed_cb(*args):
    """always succeed"""
    return False


# TestPrepareSimpleLogging {{{1
class TestPrepareSimpleLogging(unittest.TestCase):
    """Test scriptharness.log.prepare_simple_logging() method
    """
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_no_kwargs(mock_logging):
        """test_log | prepare_simple_logging with just 'path'
        """
        path = _absent_test_file()
        console_mock = mock.MagicMock()
        file_mock = mock.MagicMock()
        mock_logging.StreamHandler().setLevel = console_mock
        mock_logging.FileHandler().setLevel = file_mock
        log.prepare_simple_logging(path)
        console_mock.assert_called_once_with(log.DEFAULT_LEVEL)
        file_mock.assert_called_once_with(log.DEFAULT_LEVEL)

# TestGetFileHandler {{{1
class TestGetFileHandler(unittest.TestCase):
    """test_log | scriptharness.log.get_file_handler() method
    """
    def tearDown(self):
        assert self  # silence pylint
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_basic(mock_logging):
        """test_log | basic get_file_handler
        """
        log_file = _absent_test_file()
        formatter = mock.MagicMock()
        handler = log.get_file_handler(log_file, formatter=formatter, mode='a')
        mock_logging.FileHandler.assert_called_once_with(log_file, 'a')
        handler.setFormatter.assert_called_once_with(formatter)

    def test_overwrite(self):
        """test_log | Verify that mode='w' deletes the existing file
        """
        log_file = _present_test_file()
        logger = logging.getLogger(LOGGER_NAME)
        formatter = logging.Formatter(fmt='%(message)s')
        handler = log.get_file_handler(log_file, mode='w', formatter=formatter)
        logger.addHandler(handler)
        logger.info(TEST_STRING)
        logger.removeHandler(handler)
        handler.close()
        with open(log_file) as filehandle:
            # not sure if it's best to rstrip() here or os.linesep
            line = filehandle.readline().rstrip()
            self.assertEqual(line, TEST_STRING)

# TestGetConsoleHandler {{{1
class TestGetConsoleHandler(unittest.TestCase):
    """test_log | scriptharness.log.get_console_handler() method
    """
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_addhandler(mock_logging):
        """test_log | get_console_handler with existing log file
        """
        assert mock_logging  # shush pylint
        logger = mock.MagicMock()
        handler = log.get_console_handler(logger=logger)
        logger.addHandler.assert_called_once_with(handler)

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_handler(mock_logging):
        """test_log | basic get_console_handler
        """
        assert mock_logging  # shush pylint
        formatter = mock.MagicMock()
        handler = log.get_console_handler(formatter=formatter,
                                          level=logging.DEBUG)
        handler.setLevel.assert_called_once_with(logging.DEBUG)
        handler.setFormatter.assert_called_once_with(formatter)

# TestLogMethodInit {{{1
class TestLogMethodInit(unittest.TestCase):
    """scriptharness.log.LogMethod.__init__()
    """
    def test_no_kwargs(self):
        """test_log | LogMethod.__init__() with no keyword arguments
        """
        func = 'x'
        log_method = log.LogMethod(func)
        self.assertEqual(log_method.config, log.LogMethod.default_config)
        self.assertEqual(log_method.func, func)

    def test_illegal_kwargs(self):
        """test_log | LogMethod.__init__() with illegal keyword argument
        """
        kwargs = {
            'level': logging.WARNING,
            'illegal_scriptharness_option': 1,
        }
        self.assertRaises(
            ScriptHarnessException, log.LogMethod, 'x', **kwargs
        )

    def test_basic_decorator_return(self):
        """test_log | Basic @LogMethod decorator return
        """
        @log.LogMethod()
        def test_func(*args, **kwargs):
            """test method"""
            return args, kwargs
        pprint.pprint(log.LogMethod.default_config)
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        self.assertEqual((args, kwargs), test_func(*args, **kwargs))

    def test_illegal_callback(self):
        """test_log | LogMethod.__init__() with illegal detect_error_cb
        """
        self.assertRaises(
            ScriptHarnessException, log.LogMethod,
            'x', **{'detect_error_cb': 'y'}
        )


# TestLogMethodFunction {{{1
class TestLogMethodFunction(unittest.TestCase):
    """scriptharness.log.LogMethod wrapping a function
    """
    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_prefunc(self, mock_logging):
        """test_log | Basic @LogMethod pre_func(), function
        """
        @NoPostFunc()
        def test_func(*args, **kwargs):
            """test method"""
            return args, kwargs
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_func(*args, **kwargs)
        self.assertEqual(1, len(logger.all_messages))
        self.assertEqual(
            log.LogMethod.default_config['level'],
            logger.all_messages[0][0]
        )
        self.assertEqual(
            log.LogMethod.default_config['pre_msg'],
            logger.all_messages[0][1]
        )
        self.assertTrue(isinstance(logger.all_messages[0][2][0], dict))
        repl_dict = logger.all_messages[0][2][0]
        self.assertEqual(repl_dict['func_name'], 'test_func')
        self.assertEqual(repl_dict['args'], args)
        self.assertEqual(repl_dict['kwargs'], kwargs)
        self.assertEqual(repl_dict['return_value'], (args, kwargs))

    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_postfunc(self, mock_logging):
        """test_log | Basic @LogMethod post_func(), function
        """
        @log.LogMethod()
        def test_func(*args, **kwargs):
            """test method"""
            return args, kwargs
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_func(*args, **kwargs)
        last_message = logger.all_messages[-1]
        self.assertEqual(
            log.LogMethod.default_config['level'],
            last_message[0]
        )
        self.assertEqual(
            log.LogMethod.default_config['post_success_msg'],
            last_message[1]
        )
        self.assertTrue(isinstance(last_message[2][0], dict))
        repl_dict = last_message[2][0]
        self.assertEqual(repl_dict['func_name'], 'test_func')
        self.assertEqual(repl_dict['args'], args)
        self.assertEqual(repl_dict['kwargs'], kwargs)
        self.assertEqual(repl_dict['return_value'], (args, kwargs))

    @mock.patch('scriptharness.log.logging')
    def test_error_cb_failure(self, mock_logging):
        """test_log | @LogMethod detect_error_cb, function, fail
        """
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        for level in logging.ERROR, logging.WARNING, logging.CRITICAL:
            @log.LogMethod(detect_error_cb=always_fail_cb, error_level=level)
            def test_func(*args, **kwargs):
                """test method"""
                return args, kwargs
            logger = LoggerReplacement()
            mock_logging.getLogger.return_value = logger
            test_func(*args, **kwargs)
            self.assertEqual(2, len(logger.all_messages))
            self.assertEqual(
                level,
                logger.all_messages[-1][0]
            )
            self.assertEqual(
                log.LogMethod.default_config['post_failure_msg'],
                logger.all_messages[-1][1]
            )
            self.assertTrue(isinstance(logger.all_messages[-1][2][0], dict))
            repl_dict = logger.all_messages[-1][2][0]
            self.assertEqual(repl_dict['func_name'], 'test_func')
            self.assertEqual(repl_dict['args'], args)
            self.assertEqual(repl_dict['kwargs'], kwargs)
            self.assertEqual(repl_dict['return_value'], (args, kwargs))

    @mock.patch('scriptharness.log.logging')
    def test_error_cb_success(self, mock_logging):
        """test_log | @LogMethod detect_error_cb, function, succeed
        """
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        for level in logging.INFO, logging.DEBUG:
            @log.LogMethod(detect_error_cb=always_succeed_cb, level=level)
            def test_func(*args, **kwargs):
                """test method"""
                return args, kwargs
            logger = LoggerReplacement()
            mock_logging.getLogger.return_value = logger
            test_func(*args, **kwargs)
            self.assertEqual(2, len(logger.all_messages))
            self.assertEqual(
                level,
                logger.all_messages[1][0]
            )
            self.assertEqual(
                log.LogMethod.default_config['post_success_msg'],
                logger.all_messages[1][1]
            )
            self.assertTrue(isinstance(logger.all_messages[1][2][0], dict))
            repl_dict = logger.all_messages[1][2][0]
            self.assertEqual(repl_dict['func_name'], 'test_func')
            self.assertEqual(repl_dict['args'], args)
            self.assertEqual(repl_dict['kwargs'], kwargs)
            self.assertEqual(repl_dict['return_value'], (args, kwargs))

    @mock.patch('scriptharness.log.logging')
    def test_exception(self, mock_logging):
        """test_log | @LogMethod detect_error_cb, function, raise
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        @log.LogMethod(detect_error_cb=always_fail_cb,
                       exception=ScriptHarnessError)
        def test_func(*args, **kwargs):
            """test method"""
            return args, kwargs
        self.assertRaises(ScriptHarnessError, test_func, *args, **kwargs)
        self.assertEqual(2, len(logger.all_messages))
        self.assertEqual(
            log.LogMethod.default_config['error_level'],
            logger.all_messages[-1][0]
        )
        self.assertEqual(
            log.LogMethod.default_config['post_failure_msg'],
            logger.all_messages[-1][1]
        )
        self.assertTrue(isinstance(logger.all_messages[-1][2][0], dict))
        repl_dict = logger.all_messages[-1][2][0]
        self.assertEqual(repl_dict['func_name'], 'test_func')
        self.assertEqual(repl_dict['args'], args)
        self.assertEqual(repl_dict['kwargs'], kwargs)
        self.assertEqual(repl_dict['return_value'], (args, kwargs))

    @mock.patch('scriptharness.log.logging')
    def test_no_raise_success(self, mock_logging):
        """ test_log | @LogMethod detect_error_cb, function, don't raise on success
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        @log.LogMethod(detect_error_cb=always_succeed_cb,
                       exception=ScriptHarnessException)
        def test_func(*args, **kwargs):
            """test method"""
            return args, kwargs
        test_func(*args, **kwargs)
        self.assertEqual(2, len(logger.all_messages))
        self.assertEqual(
            log.LogMethod.default_config['level'],
            logger.all_messages[-1][0]
        )
        self.assertEqual(
            log.LogMethod.default_config['post_success_msg'],
            logger.all_messages[-1][1]
        )
        self.assertTrue(isinstance(logger.all_messages[-1][2][0], dict))
        repl_dict = logger.all_messages[-1][2][0]
        self.assertEqual(repl_dict['func_name'], 'test_func')
        self.assertEqual(repl_dict['args'], args)
        self.assertEqual(repl_dict['kwargs'], kwargs)
        self.assertEqual(repl_dict['return_value'], (args, kwargs))


# TestLogMethodClass {{{1
class TestLogMethodClass(unittest.TestCase):
    """scriptharness.log.LogMethod wrapping a class method.

    I'm not sure if these will ever fail independently of the function
    tests, so for now I'm only going to do the raise tests to verify class
    decorators work at all.
    """
    @mock.patch('scriptharness.log.logging')
    def test_exception(self, mock_logging):
        """test_log | @LogMethod detect_error_cb, class method, raise
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        class TestClass(object):
            """test class"""
            @log.LogMethod(detect_error_cb=always_fail_cb,
                           exception=ScriptHarnessError)
            def test_func(self, *args, **kwargs):
                """test method"""
                return self, args, kwargs
            def silence_pylint(self):
                """pylint complains about too few public methods"""
                pass
        test_instance = TestClass()
        self.assertRaises(ScriptHarnessError, test_instance.test_func,
                          *args, **kwargs)
        self.assertEqual(2, len(logger.all_messages))
        self.assertEqual(
            log.LogMethod.default_config['error_level'],
            logger.all_messages[-1][0]
        )
        self.assertEqual(
            log.LogMethod.default_config['post_failure_msg'],
            logger.all_messages[-1][1]
        )
        self.assertTrue(isinstance(logger.all_messages[-1][2][0], dict))
        repl_dict = logger.all_messages[-1][2][0]
        self.assertEqual(repl_dict['func_name'], 'test_func')
        self.assertEqual(
            repl_dict['args'], tuple([test_instance] + list(args))
        )
        self.assertEqual(repl_dict['kwargs'], kwargs)
        self.assertEqual(
            repl_dict['return_value'], (test_instance, args, kwargs)
        )

    @mock.patch('scriptharness.log.logging')
    def test_no_raise_success(self, mock_logging):
        """test_log | @LogMethod detect_error_cb, class method, don't raise on success
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        class TestClass(object):
            """test class"""
            @log.LogMethod(detect_error_cb=always_succeed_cb,
                           exception=ScriptHarnessError)
            def test_func(self, *args, **kwargs):
                """test method"""
                return self, args, kwargs
            def silence_pylint(self):
                """pylint complains about too few public methods"""
                pass
        test_instance = TestClass()
        test_instance.test_func(*args, **kwargs)
        self.assertEqual(2, len(logger.all_messages))
        self.assertEqual(
            log.LogMethod.default_config['level'],
            logger.all_messages[-1][0]
        )
        self.assertEqual(
            log.LogMethod.default_config['post_success_msg'],
            logger.all_messages[-1][1]
        )
        self.assertTrue(isinstance(logger.all_messages[-1][2][0], dict))
        repl_dict = logger.all_messages[-1][2][0]
        self.assertEqual(repl_dict['func_name'], 'test_func')
        self.assertEqual(
            repl_dict['args'], tuple([test_instance] + list(args))
        )
        self.assertEqual(repl_dict['kwargs'], kwargs)
        self.assertEqual(
            repl_dict['return_value'],
            (test_instance, args, kwargs)
        )


# TestUnicode {{{1
class TestUnicode(unittest.TestCase):
    """Test stdout + file logging, for real, to verify unicode
    """
    def tearDown(self):
        for path in (TEST_FILE, TEST_CONSOLE):
            if os.path.exists(path):
                os.remove(path)
        assert self  # silence pylint

    @staticmethod
    @contextmanager
    def get_file_logger():
        """Create a logger with a file handler for testing.

        The formatter is a UnicodeFormatter with a fmt of %(message)s for
        simplified message verification.
        """
        file_log = _absent_test_file(TEST_FILE)
        formatter = log.UnicodeFormatter(fmt='%(message)s')
        file_handler = log.get_file_handler(
            file_log, formatter=formatter, mode='w'
        )
        logger = logging.getLogger(LOGGER_NAME)
        logger.addHandler(file_handler)
        try:
            yield logger
        finally:
            logger.removeHandler(file_handler)
            file_handler.close()

    @staticmethod
    def get_console_logger():
        """Create a logger with a console handler for testing.

        The formatter is a UnicodeFormatter with a fmt of %(message)s for
        simplified message verification.
        """
        formatter = log.UnicodeFormatter(fmt='%(message)s')
        console_handler = log.get_console_handler(formatter=formatter)
        logger = logging.getLogger(LOGGER_NAME)
        logger.handlers = []
        logger.addHandler(console_handler)
        return logger

    def test_unicode_file(self):
        """test_log | unicode strings to a file
        """
        for string in UNICODE_STRINGS:
            with stdstar_redirected(TEST_CONSOLE):
                with self.get_file_logger() as logger:
                    logger.info(string)
            with codecs.open(TEST_FILE, 'r', 'utf-8') as filehandle:
                line = filehandle.read().rstrip()
                self.assertEqual(string, line)

    def test_unicode_console(self):
        """test_log | bare unicode strings to a console
        """
        for string in UNICODE_STRINGS:
            with stdstar_redirected(TEST_CONSOLE):
                logger = self.get_console_logger()
                logger.info(string)
            with codecs.open(TEST_CONSOLE, 'r', 'utf-8') as console_fh:
                self.assertEqual(string, console_fh.read().rstrip())


# TestOutputBuffer {{{1
class TestOutputBuffer(unittest.TestCase):
    """Test OutputBuffer.
    """
    def test_single_pop(self):
        """test_log | OutputBuffer single pop_buffer
        """
        logger = mock.MagicMock()
        buf = log.OutputBuffer(logger, 3, 0)
        buf.add_line(0, "foo%s", "a")
        buf.add_line(0, "bar%s", "b")
        buf.add_line(0, "baz")
        self.assertFalse(logger.log.called)
        buf.add_line(0, "x")
        logger.log.assert_called_once_with(0, "foo%s", "a")

    @mock.patch('scriptharness.log.logging')
    def test_pre_context_lines(self, mock_logging):
        """test_log | OutputBuffer pre_context_lines
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        buf = log.OutputBuffer(logger, 4, 0)
        buf.add_line(0, "foo", "a")
        buf.add_line(0, "bar")
        buf.add_line(0, "baz", "c")
        buf.add_line(10, "x", pre_context_lines=2)
        buf.dump_buffer()
        pprint.pprint(logger.all_messages)
        self.assertEqual(logger.all_messages[0], (0, "foo", ("a", )))
        self.assertEqual(logger.all_messages[1], (10, "bar", ()))
        self.assertEqual(logger.all_messages[2], (10, "baz", ("c", )))
        self.assertEqual(logger.all_messages[3], (10, "x", ()))

    @mock.patch('scriptharness.log.logging')
    def test_post_context_lines(self, mock_logging):
        """test_log | OutputBuffer post_context_lines
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        buf = log.OutputBuffer(logger, 0, 3)
        buf.add_line(0, "foo")
        buf.add_line(10, "bar", post_context_lines=3)
        buf.add_line(15, "baz", "c", post_context_lines=1)
        buf.add_line(0, "x")
        buf.add_line(0, "y")
        buf.add_line(0, "z")
        pprint.pprint(logger.all_messages)
        self.assertEqual(logger.all_messages[0], (0, "foo", ()))
        self.assertEqual(logger.all_messages[1], (10, "bar", ()))
        self.assertEqual(logger.all_messages[2], (15, "baz", ("c", )))
        self.assertEqual(logger.all_messages[3], (15, "x", ()))
        self.assertEqual(logger.all_messages[4], (10, "y", ()))
        self.assertEqual(logger.all_messages[5], (0, "z", ()))


# TestOutputParser {{{1
class TestOutputParser(unittest.TestCase):
    """Test OutputParser.
    """
    @staticmethod
    def get_output_parser(error_list, **kwargs):
        """helper to create OutputParser
        """
        logger = LoggerReplacement()
        return log.OutputParser(
            error_list, logger=logger,
            **kwargs
        )

    def test_simple_add_line(self):
        """test_log | OutputParser simple add_line()
        """
        for error_list in (
                [{'substr': 'asdf', 'level': logging.ERROR,
                  'explanation': "because"}],
                [{'regex': re.compile('asdf'), 'level': logging.ERROR,
                  'explanation': "because"}]):
            print(error_list)
            error_list = ErrorList(error_list)
            output_parser = self.get_output_parser(error_list)
            output_parser.add_line("foo")
            self.assertEqual(
                output_parser.logger.all_messages[0],
                (logging.INFO, ' foo', ())
            )
            output_parser.add_line("barasdfbaz")
            self.assertEqual(
                output_parser.logger.all_messages[1],
                (logging.ERROR, ' barasdfbaz', ())
            )
            self.assertEqual(
                output_parser.logger.all_messages[2],
                (logging.ERROR, ' because', ())
            )
            self.assertEqual(output_parser.history['num_errors'], 1)
            self.assertEqual(output_parser.history['num_warnings'], 0)

    def test_ignore(self):
        """test_log | OutputParser ignore
        """
        error_list = ErrorList([{'substr': 'asdf', 'level': -1}])
        # The foo="bar" does nothing except more code coverage
        output_parser = self.get_output_parser(error_list, foo="bar")
        output_parser.add_line("barasdfbaz")
        self.assertEqual(0, len(output_parser.logger.all_messages))
        output_parser.add_line("foo")
        self.assertEqual(
            output_parser.logger.all_messages,
            [(logging.INFO, ' foo', ())]
        )

    def test_warning(self):
        """test_log | OutputParser warning
        """
        error_list = ErrorList(
            [{'substr': 'asdf', 'level': logging.WARNING}]
        )
        output_parser = self.get_output_parser(error_list)
        output_parser.add_line("barasdfbaz")
        self.assertEqual(
            output_parser.logger.all_messages,
            [(logging.WARNING, ' barasdfbaz', ())]
        )
        self.assertEqual(output_parser.history['num_errors'], 0)
        self.assertEqual(output_parser.history['num_warnings'], 1)

    def test_exception_context_lines(self):
        """test_log | OutputParser exception context_lines
        """
        error_list = ErrorList(
            [{'substr': 'asdf', 'exception': ScriptHarnessError,
              'pre_context_lines': 2,
              'explanation': "because"}]
        )
        output_parser = self.get_output_parser(error_list)
        output_parser.add_line("This line will be INFO")
        output_parser.add_line("Start of the ERROR")
        self.assertEqual(0, len(output_parser.logger.all_messages))
        output_parser.add_line("Middle of the ERROR")
        self.assertEqual(
            output_parser.logger.all_messages,
            [(logging.INFO, " This line will be INFO", ())]
        )
        self.assertRaises(
            ScriptHarnessError,
            output_parser.add_line, "ERROR asdf"
        )
        self.assertEqual(
            output_parser.logger.all_messages[1],
            (logging.ERROR, " Start of the ERROR", ())
        )
        self.assertEqual(
            output_parser.logger.all_messages[2],
            (logging.ERROR, " Middle of the ERROR", ())
        )
        self.assertEqual(
            output_parser.logger.all_messages[3],
            (logging.ERROR, " ERROR asdf", ())
        )
        self.assertEqual(
            output_parser.logger.all_messages[4],
            (logging.ERROR, " because", ())
        )
        self.assertEqual(len(output_parser.logger.all_messages), 5)

    def test_exception(self):
        """test_log | OutputParser exception
        """
        error_list = ErrorList(
            [{'substr': 'asdf', 'exception': ScriptHarnessError,
              'level': logging.WARNING}]
        )
        output_parser = self.get_output_parser(error_list)
        output_parser.add_line("This line will be INFO")
        self.assertEqual(
            output_parser.logger.all_messages,
            [(logging.INFO, " This line will be INFO", ())]
        )
        self.assertRaises(
            ScriptHarnessError,
            output_parser.add_line, "WARNING asdf"
        )
        self.assertEqual(
            output_parser.logger.all_messages[1],
            (logging.WARNING, " WARNING asdf", ())
        )
        self.assertEqual(len(output_parser.logger.all_messages), 2)
