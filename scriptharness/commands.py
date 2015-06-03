#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Commands, largely through subprocess.

Attributes:
  LOGGER_NAME (str): default logging.Logger name.
  STRINGS (dict): Strings for logging.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from copy import deepcopy
import logging
import multiprocessing
import os
import six
import pprint
from scriptharness.exceptions import ScriptHarnessError, \
    ScriptHarnessException, ScriptHarnessFatal, ScriptHarnessTimeout
from scriptharness.log import OutputParser, ErrorList
import scriptharness.process
import scriptharness.status
from scriptharness.unicode import to_unicode
import subprocess

LOGGER_NAME = "scriptharness.commands"
STRINGS = {
    "check_output": {
        "pre_msg":
            "Running subprocess.check_output() with %(args)s %(kwargs)s",
    },
    "command": {
        "cwd_doesn't_exist":
            "Can't run command %(command)s in non-existent directory %(cwd)s!",
        "start_with_cwd": "Running command: %(command)s in %(cwd)s",
        "start_without_cwd": "Running command: %(command)s",
        "copy_paste": "Copy/paste: %(command)s",
        "output_timeout":
            "Command %(command)s timed out after %(output_timeout)d "
            "seconds without output.",
        "timeout":
            "Command %(command)s timed out after %(run_time)d seconds.",
        "error": "Command %(command)s failed.",
        "env": "Using env: %(env)s",
        "kill_hung_process": "Killing process that's still here",
    },
}


# Functions {{{1
def check_output(command, logger_name="scriptharness.commands.check_output",
                 level=logging.INFO, log_output=True, **kwargs):
    """Wrap subprocess.check_output with logging

    Args:
      command (str or list): The command to run.
      logger_name (str, optional): the logger name to log with.
      level (int, optional): the logging level to log with.  Defaults to
        logging.INFO
      log_output (bool, optional): When true, log the output of the command.
        Defaults to True.
      **kwargs: sent to `subprocess.check_output()`
    """
    logger = logging.getLogger(logger_name)
    logger.log(level, STRINGS['check_output']['pre_msg'],
               {'args': (), 'kwargs': kwargs})
    output = subprocess.check_output(command, **kwargs)
    if log_output:
        logger = logging.getLogger(logger_name)
        logger.info("Output:")
        for line in output.splitlines():
            logger.log(level, " %s", line)
    return output


# Command and helpers {{{1
def detect_errors(command):
    """ Very basic detect_errors_cb for Command.

    This looks in the command.history for return_value.  If this is set
    to 0 or other null value other than None, the command is successful.
    Otherwise it's unsuccessful.

    Args:
      command (Command obj):
    """
    status = scriptharness.status.SUCCESS
    return_value = command.history.get('return_value')
    if return_value is None or return_value:
        status = scriptharness.status.ERROR
    return status

class Command(object):
    """Basic command: run and log output.

    Attributes:
      command (list or string): The command to send to subprocess.Popen

      logger (logging.Logger): logger to log with.

      detect_error_cb (function): this function determines whether the
        command was successful.

      history (dict): This dictionary holds the timestamps and status of
        the command.

      kwargs (dict): These kwargs will be passed to subprocess.Popen, except
        for the optional 'output_timeout' and 'timeout', which are processed by
        Command.  `output_timeout` is how long a command can run without
        outputting anything to the screen/log.  `timeout` is how long the
        command can run, total.

      strings (dict): Strings to log.
    """
    def __init__(self, command, logger=None, detect_error_cb=None, **kwargs):
        self.command = command
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self.detect_error_cb = detect_error_cb or detect_errors
        if not hasattr(self, 'history'):
            self.history = {}
        self.kwargs = kwargs or {}
        self.strings = deepcopy(STRINGS['command'])
        self.process = None

    def log_env(self, env):
        """Log environment variables.  Here for subclassing.

        Args:
          env (dict): the environment we'll be passing to subprocess.Popen.
        """
        env = self.fix_env(env)
        self.logger.info(self.strings['env'], {'env': pprint.pformat(env)})

    @staticmethod
    def fix_env(env):
        """Windows environments are fiddly.

        Args:
          env (dict): the environment we'll be passing to subprocess.Popen.
        """
        if os.name == 'nt':
            env.setdefault("SystemRoot", os.environ["SystemRoot"])
            if six.PY2:
                new_env = {}
                # Win Py2 unhappy with unicode env vars
                for key, value in env.items():
                    if isinstance(key, six.text_type):
                        key = six.binary_type(key)
                    if isinstance(value, six.text_type):
                        value = six.binary_type(value)
                    new_env[key] = value
                env = new_env
        return env

    def log_start(self):
        """Log the start of the command, also checking for the existence of
        cwd if defined.

        Raises:
          scriptharness.exceptions.ScriptHarnessException: if cwd is defined
            and doesn't exist.
        """
        if 'cwd' in self.kwargs:
            if not os.path.isdir(self.kwargs['cwd']):
                raise ScriptHarnessException(
                    self.strings["cwd_doesn't_exist"] % \
                    {'cwd': self.kwargs['cwd'], 'command': self.command}
                )
            self.logger.info(
                self.strings["start_with_cwd"],
                {'cwd': self.kwargs['cwd'], 'command': self.command}
            )
        else:
            self.logger.info(
                self.strings["start_without_cwd"], {'command': self.command}
            )
        if isinstance(self.command, (list, tuple)):
            self.logger.info(
                self.strings["copy_paste"],
                {'command': subprocess.list2cmdline(self.command)}
            )
        if 'env' in self.kwargs:
            # https://mail.python.org/pipermail/python-dev/2011-December/114740.html
            self.log_env(self.kwargs['env'])

    def add_line(self, line):
        """Log the output.  Here for subclassing.

        Args:
          line (str): a line of output
        """
        self.logger.info(" %s", to_unicode(line.rstrip()))

    def finish_process(self):
        """Here for subclassing.
        """
        pass

    def run(self):
        """Run the command.

        Raises:
          scriptharness.exceptions.ScriptHarnessError on error
        """
        if 'env' in self.kwargs:
            self.kwargs['env'] = self.fix_env(self.kwargs['env'])
        self.log_start()
        output_timeout = self.kwargs.get('output_timeout', None)
        if 'output_timeout' in self.kwargs:
            del self.kwargs['output_timeout']
        max_timeout = self.kwargs.get('timeout', None)
        if 'timeout' in self.kwargs:
            del self.kwargs['timeout']
        if isinstance(self.command, (list, tuple)):
            self.kwargs.setdefault('shell', False)
        else:
            self.kwargs.setdefault('shell', True)
        queue = multiprocessing.Queue()
        runner = multiprocessing.Process(
            target=scriptharness.process.run_subprocess,
            args=(queue, self.command),
            kwargs=self.kwargs,
        )
        runner.start()
        self.history['return_value'] = scriptharness.process.watch_runner(
            self.logger, queue, runner, self.add_line,
            output_timeout=output_timeout, max_timeout=max_timeout
        )
        self.history['status'] = self.detect_error_cb(self)
        if self.history['status'] != scriptharness.status.SUCCESS:
            raise ScriptHarnessError(
                self.strings["error"] % {'command': self.command,}
            )


def run(command, halt_on_failure=False, **kwargs):
    """Shortcut for running a Command.

    Not entirely sure if this should also catch ScriptHarnessFatal, as those
    are explicitly trying to kill the script.

    Args:
      command (list or str): Command line to run.
      **kwargs: kwargs for subprocess.Popen.

    Returns:
      command exit code (int)

    Raises:
      scriptharness.exceptions.ScriptHarnessFatal: on fatal error
    """
    message = ""
    try:
        cmd = Command(command, **kwargs)
        return cmd.run()
    except ScriptHarnessError as exc_info:
        message = "error: %s" % exc_info
        status = scriptharness.status.ERROR
    except ScriptHarnessTimeout as exc_info:
        message = "timeout: %s" % exc_info
        status = scriptharness.status.TIMEOUT
    if halt_on_failure and message:
        raise ScriptHarnessFatal("Fatal %s" % message)
    else:
        return status


# ParsedCommand {{{1
class ParsedCommand(OutputParser, Command):
    """Parse each line of output for errors.
    """
    def __init__(self, command, error_list, **kwargs):
        if not isinstance(error_list, ErrorList):
            raise ScriptHarnessException(
                "error_list must be an ErrorList!",
                error_list
            )
        OutputParser.__init__(self, error_list)
        Command.__init__(self, command, **kwargs)

# Output {{{1
class Output(Command):
    """
    TODO: binary mode? silent is kinda like that.
    TODO: since p.wait() can take a long time, optionally log something
    every N seconds?
    TODO: optionally only return the tmp_stdout_filename?
    """

##def get_output_from_command(context, command, cwd=None,
##                            halt_on_failure=False, env=None,
##                            silent=False, log_level=INFO,
##                            tmpfile_base_path='tmpfile',
##                            return_type='output', save_tmpfiles=False,
##                            throw_exception=False, fatal_exit_code=2,
##                            ignore_errors=False, success_codes=None):
##    """Similar to run_command, but where run_command is an
##    os.system(command) analog, get_output_from_command is a `command`
##    analog.
##
##    Less error checking by design, though if we figure out how to
##    do it without borking the output, great.
##
##
##    ignore_errors=True is for the case where a command might produce standard
##    error output, but you don't particularly care; setting to True will
##    cause standard error to be logged at DEBUG rather than ERROR
##    """
##    if cwd:
##        if not os.path.isdir(cwd):
##            level = logging.ERROR
##            if halt_on_failure:
##                level = logging.FATAL
##            context.logger.log("Can't run command %s in non-existent directory %s!" %
##                     (command, cwd), level=level)
##            return None
##        context.logger.info("Getting output from command: %s in %s" % (command, cwd))
##    else:
##        context.logger.info("Getting output from command: %s" % command)
##    if isinstance(command, list):
##        context.logger.info("Copy/paste: %s" % subprocess.list2cmdline(command))
##    # This could potentially return something?
##    tmp_stdout = None
##    tmp_stderr = None
##    tmp_stdout_filename = '%s_stdout' % tmpfile_base_path
##    tmp_stderr_filename = '%s_stderr' % tmpfile_base_path
##    if success_codes is None:
##        success_codes = [0]
##
##    try:
##        tmp_stdout = open(tmp_stdout_filename, 'w')
##    except IOError:
##        level = logging.ERROR
##        if halt_on_failure:
##            level = logging.FATAL
##        context.logger.log("Can't open %s for writing!" % tmp_stdout_filename +
##                 self.exception(), level=level)
##        return None
##    try:
##        tmp_stderr = open(tmp_stderr_filename, 'w')
##    except IOError:
##        level = logging.ERROR
##        if halt_on_failure:
##            level = logging.FATAL
##        context.logger.log("Can't open %s for writing!" % tmp_stderr_filename +
##                 self.exception(), level=level)
##        return None
##    shell = True
##    if isinstance(command, list):
##        shell = False
##    p = subprocess.Popen(command, shell=shell, stdout=tmp_stdout,
##                         cwd=cwd, stderr=tmp_stderr, env=env)
##    context.logger.log(
##        "Temporary files: %s and %s" % (
##            tmp_stdout_filename, tmp_stderr_filename), level=logging.DEBUG)
##    p.wait()
##    tmp_stdout.close()
##    tmp_stderr.close()
##    return_level = logging.DEBUG
##    output = None
##    if os.path.exists(tmp_stdout_filename) and os.path.getsize(tmp_stdout_filename):
##        output = read_from_file(tmp_stdout_filename,
##                                     verbose=False)
##        if not silent:
##            context.logger.log("Output received:", level=log_level)
##            output_lines = output.rstrip().splitlines()
##            for line in output_lines:
##                if not line or line.isspace():
##                    continue
##                line = line.decode("utf-8")
##                context.logger.log(' %s' % line, level=log_level)
##            output = '\n'.join(output_lines)
##    if os.path.exists(tmp_stderr_filename) and os.path.getsize(tmp_stderr_filename):
##        if not ignore_errors:
##            return_level = logging.ERROR
##        context.logger.log("Errors received:", level=return_level)
##        errors = read_from_file(tmp_stderr_filename,
##                                     verbose=False)
##        for line in errors.rstrip().splitlines():
##            if not line or line.isspace():
##                continue
##            line = line.decode("utf-8")
##            context.logger.log(' %s' % line, level=return_level)
##    elif p.returncode not in success_codes and not ignore_errors:
##        return_level = logging.ERROR
##    # Clean up.
##    if not save_tmpfiles:
##        self.rmtree(tmp_stderr_filename, log_level=logging.DEBUG)
##        self.rmtree(tmp_stdout_filename, log_level=logging.DEBUG)
##    if p.returncode and throw_exception:
##        raise subprocess.CalledProcessError(p.returncode, command)
##    context.logger.log("Return code: %d" % p.returncode, level=return_level)
##    if halt_on_failure and return_level == logging.ERROR:
##        return_code = fatal_exit_code
##        raise ScriptHarnessFatal(
##            "Halting on failure while running %s" % command
##        )
##    # Hm, options on how to return this? I bet often we'll want
##    # output_lines[0] with no newline.
##    if return_type != 'output':
##        return (tmp_stdout_filename, tmp_stderr_filename)
##    else:
##        return output